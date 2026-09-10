"""Browser-extension API routes: pair, capture, promote, status (G-1390 / G-1391).

The extension authenticates with a DEDICATED token (see services.extension_pairing)
that is separate from the global AUTH_API_KEY and required even when AUTH_ENABLED is
off. `/pair` is the bootstrap (code-gated, no token yet); `/capture`, `/promote`
and `/status` require a valid extension token via `require_extension_token`.

Part B (G-1391): `/capture` is now real — it dedupes + scores the captured job by
REUSING `services.extension_capture.capture_and_score` (which calls
`services.scoring.score_job`; the prompt is never reimplemented here). `/promote`
adds a captured job to the pipeline via the shared
`services.discovery.promote_discovered_job_to_application` service.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from career_os import __version__
from career_os.ai.base import ProviderQuotaError
from career_os.ai.openrouter_provider import CreditsExhaustedError
from career_os.api.oauth import limiter
from career_os.config import settings
from career_os.database import get_db
from career_os.models.models import Profile
from career_os.schemas.extension import (
    CaptureRequest,
    CaptureResponse,
    InstanceInfo,
    PairRequest,
    PairResponse,
    PromoteRequest,
    PromoteResponse,
    StatusResponse,
)
from career_os.schemas.scoring import score_to_letter_grade
from career_os.services.discovery import (
    DiscoveredJobNotFoundError,
    promote_discovered_job_to_application,
)
from career_os.services.extension_capture import (
    CaptureIncompleteError,
    CaptureTooLargeError,
    build_plain_language_gap,
    capture_and_score,
)
from career_os.services.extension_pairing import (
    consume_pairing_code,
    extension_token_account,
    mint_extension_token,
)
from career_os.services.scoring import (
    ProfileIncompleteError,
    ProfileNotFoundError,
    ScoringError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/extension", tags=["extension"])

# Brand name surfaced to the extension. Deliberately "Kestrel" (project brand) and
# NOT settings.app_name ("Career OS", the internal package name) — T-00-03.
_INSTANCE_NAME = "Kestrel"


def _instance_info() -> InstanceInfo:
    return InstanceInfo(name=_INSTANCE_NAME, version=__version__)


def require_extension_token(
    authorization: Annotated[str | None, Header()] = None,
) -> int | None:
    """Validate dedicated bearer token and return its bound account ID."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Extension not paired")
    token = authorization[7:]
    account_id = extension_token_account(token)
    if account_id is False:
        raise HTTPException(status_code=401, detail="Extension not paired")
    if settings.shoo_auth_enabled and account_id is None:
        raise HTTPException(status_code=401, detail="Extension not paired")
    return account_id


@router.post(
    "/pair",
    response_model=PairResponse,
    responses={429: {"description": "Too many pairing attempts"}},
)
@limiter.limit("5/minute")
def pair(request: Request, payload: PairRequest) -> PairResponse:
    """Consume pairing code and mint dedicated account-bound token."""
    account_id = consume_pairing_code(payload.pairing_code)
    if account_id is False:
        raise HTTPException(status_code=401, detail="Invalid or expired pairing code")
    if settings.shoo_auth_enabled and type(account_id) is not int:
        raise HTTPException(status_code=401, detail="Pairing requires an account")
    owner_id = account_id if type(account_id) is int else None
    return PairResponse(token=mint_extension_token(owner_id), instance=_instance_info())


@router.post("/capture", response_model=CaptureResponse)
async def capture(
    payload: CaptureRequest,
    account_id: Annotated[int | None, Depends(require_extension_token)],
    db: Annotated[Session, Depends(get_db)],
) -> CaptureResponse:
    """Dedupe + score a captured job, returning its score, breakdown and gap.

    Scoring is delegated to ``services.extension_capture.capture_and_score`` which
    reuses ``services.scoring.score_job`` — the prompt is NOT reimplemented here.
    Domain exceptions map to HTTP mirroring ``api/scoring.py`` (T-01B-04: the
    response is an explicit Pydantic model, never a raw ORM dump).
    """
    profile_id = 1
    if account_id is not None:
        profile = (
            db.query(Profile).filter(Profile.account_id == account_id).order_by(Profile.id).first()
        )
        if profile is None:
            raise HTTPException(status_code=401, detail="Extension owner not found")
        profile_id = profile.id
    try:
        dj, scored = await capture_and_score(db, payload, profile_id=profile_id)
    except CaptureTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except CaptureIncompleteError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProfileIncompleteError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (CreditsExhaustedError, ProviderQuotaError) as exc:
        raise HTTPException(
            status_code=402, detail=f"AI provider credits exhausted: {exc}"
        ) from exc
    except ScoringError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive 500
        # Never surface internal exception text to the client (SECURITY F-4); the
        # real error is logged server-side via logger.exception.
        logger.exception("Extension capture failed")
        raise HTTPException(status_code=500, detail="Capture failed") from exc

    breakdown: list | None = None
    if scored.score_breakdown:
        try:
            parsed = json.loads(scored.score_breakdown)
            breakdown = parsed if isinstance(parsed, list) else None
        except (json.JSONDecodeError, ValueError):
            breakdown = None

    return CaptureResponse(
        job_id=str(dj.id),
        status="scored",
        scored=True,
        discovered_job_id=dj.id,
        fit_score=scored.fit_score,
        letter_grade=score_to_letter_grade(scored.fit_score),
        score_breakdown=breakdown,
        gap=build_plain_language_gap(scored),
    )


@router.post("/promote", response_model=PromoteResponse)
def promote(
    payload: PromoteRequest,
    account_id: Annotated[int | None, Depends(require_extension_token)],
    db: Annotated[Session, Depends(get_db)],
) -> PromoteResponse:
    """Add a captured DiscoveredJob to the pipeline (idempotent one-click promote).

    Delegates to the shared ``promote_discovered_job_to_application`` service with
    ``source="extension"``; a second call for the same job returns the same
    Application (the DiscoveredJob↔Application link is ``DiscoveredJob.application_id``).
    """
    profile_id = 1
    if account_id is not None:
        profile = (
            db.query(Profile).filter(Profile.account_id == account_id).order_by(Profile.id).first()
        )
        if profile is None:
            raise HTTPException(status_code=401, detail="Extension owner not found")
        profile_id = profile.id
    try:
        app = promote_discovered_job_to_application(
            db,
            profile_id=profile_id,
            discovered_job_id=payload.discovered_job_id,
            source="extension",
            notes=None,
        )
        db.commit()
    except DiscoveredJobNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive 500
        db.rollback()
        # Generic client detail; internal error stays server-side (SECURITY F-4).
        logger.exception("Extension promote failed")
        raise HTTPException(status_code=500, detail="Promote failed") from exc

    return PromoteResponse(application_id=app.id, status=app.status)


@router.get("/status", response_model=StatusResponse)
def status(
    _account_id: Annotated[int | None, Depends(require_extension_token)],
) -> StatusResponse:
    """Report instance info to a paired extension (health/identity check)."""
    return StatusResponse(ok=True, instance=_instance_info())
