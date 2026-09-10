"""Request dependencies for authenticated account and profile ownership."""

import json
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from career_os.config import settings
from career_os.database import get_db
from career_os.models.auth import Account, AuthSession
from career_os.models.models import Profile
from career_os.services.auth import csrf_valid, get_session

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_CSRF_HEADER = "x-csrf-token"


def current_session(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> AuthSession | None:
    """Resolve browser session; preserve unauthenticated local mode when disabled."""
    if not settings.shoo_auth_enabled:
        return None
    session = get_session(db, request.cookies.get(settings.session_cookie_name))
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def current_account(
    session: Annotated[AuthSession | None, Depends(current_session)],
) -> Account | None:
    """Resolve authenticated account."""
    return session.account if session else None


async def authorize_private_request(
    request: Request,
    session: Annotated[AuthSession | None, Depends(current_session)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Gate private requests, enforce CSRF, and reject foreign profile IDs."""
    if session is None:
        return
    if request.method not in _SAFE_METHODS and not csrf_valid(
        session, request.headers.get(_CSRF_HEADER)
    ):
        raise HTTPException(status_code=403, detail="CSRF validation failed")

    candidate_ids = [
        request.path_params.get("profile_id"),
        request.query_params.get("profile_id"),
    ]
    if request.method not in _SAFE_METHODS:
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                body = json.loads(await request.body())
            except json.JSONDecodeError:
                body = None
            if isinstance(body, dict):
                candidate_ids.append(body.get("profile_id"))

    for candidate in candidate_ids:
        if candidate is None:
            continue
        try:
            profile_id = int(candidate)
        except (TypeError, ValueError):
            continue
        owned = (
            db.query(Profile.id)
            .filter(Profile.id == profile_id, Profile.account_id == session.account_id)
            .first()
        )
        if owned is None:
            raise HTTPException(status_code=404, detail="Profile not found")


def owned_profile(
    profile_id: int,
    account: Annotated[Account | None, Depends(current_account)],
    db: Annotated[Session, Depends(get_db)],
) -> Profile:
    """Resolve profile only when it belongs to authenticated account."""
    filters = [Profile.id == profile_id]
    if account is not None:
        filters.append(Profile.account_id == account.id)
    profile = db.query(Profile).filter(*filters).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
