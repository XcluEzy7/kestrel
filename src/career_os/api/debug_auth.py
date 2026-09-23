"""Explicitly enabled debug-only browser authentication."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from career_os.api.shoo_auth import set_session_cookies
from career_os.config import settings
from career_os.database import get_db
from career_os.services.auth import account_for_claims, create_session, default_profile

router = APIRouter(prefix="/api/auth", tags=["auth"])
DEBUG_PAIRWISE_SUB = "debug:kst-6"


class DebugLoginRequest(BaseModel):
    """Shared secret submitted to explicitly opt into debug authentication."""

    secret: str = Field(..., min_length=1, max_length=4096)


@router.post("/debug")
def debug_login(
    payload: DebugLoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Create normal session for dedicated debug identity when explicitly enabled."""
    if not settings.debug_auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not settings.debug_auth_secret or not secrets.compare_digest(
        payload.secret, settings.debug_auth_secret
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid debug secret")

    account = account_for_claims(
        db,
        {"pairwise_sub": DEBUG_PAIRWISE_SUB, "name": "Debug User", "email": None},
        claim_legacy=False,
    )
    token, csrf, _ = create_session(db, account)
    set_session_cookies(response, token, csrf)
    return {"authenticated": True, "debug": True, "profile_id": default_profile(account).id}
