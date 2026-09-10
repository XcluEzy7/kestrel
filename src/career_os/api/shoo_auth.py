"""Shoo login and secure browser-session endpoints."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from career_os.config import settings
from career_os.database import get_db
from career_os.models.auth import Account, MCPToken
from career_os.services.auth import (
    account_for_claims,
    create_session,
    csrf_valid,
    default_profile,
    get_session,
    session_cookie_kwargs,
    verify_shoo_token,
)

router = APIRouter(prefix="/api/auth/shoo", tags=["auth"])


class ShooLoginRequest(BaseModel):
    """Shoo ID token submitted by browser after Shoo sign-in."""

    id_token: str = Field(..., min_length=1, max_length=16384)


class MCPTokenCreateRequest(BaseModel):
    """Request for an account's default-profile MCP token."""

    name: str = Field(default="MCP client", min_length=1, max_length=100)
    scopes: set[str] = Field(default_factory=lambda: {"mcp:read"})
    expires_in_days: int | None = Field(default=None, ge=1, le=365)

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: set[str]) -> set[str]:
        allowed = {"mcp:read", "mcp:write"}
        if not value or not value <= allowed:
            raise ValueError("scopes must contain mcp:read and/or mcp:write")
        return value


class MCPTokenResponse(BaseModel):
    id: int
    name: str
    token_prefix: str
    scopes: list[str]
    profile_id: int
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class MCPTokenCreatedResponse(MCPTokenResponse):
    token: str


@router.post("/login")
def login(
    payload: ShooLoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Verify Shoo token and establish opaque server-side session."""
    try:
        claims = verify_shoo_token(payload.id_token, app_origin=settings.shoo_app_origin)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid Shoo identity token") from exc
    account = account_for_claims(db, claims)
    token, csrf, _ = create_session(db, account)
    response.set_cookie(settings.session_cookie_name, token, **session_cookie_kwargs())
    response.set_cookie(
        "kestrel_csrf",
        csrf,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    try:
        profile_id = default_profile(account).id
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail="Authenticated account has no profile") from exc
    return {"authenticated": True, "profile_id": profile_id}


@router.post("/logout")
def logout(request: Request, response: Response, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Revoke current server session and clear browser cookies."""
    session = get_session(db, request.cookies.get(settings.session_cookie_name))
    if session is not None and not csrf_valid(session, request.headers.get("x-csrf-token")):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    if session is not None:
        db.delete(session)
        db.commit()
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        "kestrel_csrf", path="/", secure=settings.session_cookie_secure, samesite="lax"
    )
    return {"authenticated": False}


@router.get("/me")
def me(request: Request, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return auth state and server-authoritative default profile."""
    session = get_session(db, request.cookies.get(settings.session_cookie_name))
    if session is None:
        return {"authenticated": False}
    try:
        profile_id = default_profile(session.account).id
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail="Authenticated account has no profile") from exc
    return {"authenticated": True, "profile_id": profile_id}


def _token_response(token: MCPToken, secret: str | None = None) -> dict:
    result = MCPTokenResponse(
        id=token.id,
        name=token.name,
        token_prefix=token.token_prefix,
        scopes=sorted(token.scopes.split()),
        profile_id=token.profile_id,
        expires_at=token.expires_at,
        revoked_at=token.revoked_at,
        created_at=token.created_at,
    ).model_dump(mode="json")
    if secret is not None:
        result["token"] = secret
    return result


def _browser_account(request: Request, db: Session) -> Account:
    session = get_session(db, request.cookies.get(settings.session_cookie_name))
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not csrf_valid(session, request.headers.get("x-csrf-token")):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    return session.account


@router.post("/mcp-tokens", status_code=201, response_model=MCPTokenCreatedResponse)
def create_mcp_token(
    payload: MCPTokenCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Create one scoped token bound to caller's server-selected default profile."""
    account = _browser_account(request, db)
    profile = default_profile(account)
    token = "kst_mcp_" + secrets.token_urlsafe(32)
    record = MCPToken(
        account_id=account.id,
        profile_id=profile.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        token_prefix=token[:12],
        name=payload.name,
        scopes=" ".join(sorted(payload.scopes)),
        expires_at=(
            datetime.now(UTC) + timedelta(days=payload.expires_in_days)
            if payload.expires_in_days
            else None
        ),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _token_response(record, token)


@router.get("/mcp-tokens", response_model=list[MCPTokenResponse])
def list_mcp_tokens(request: Request, db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    """List account tokens without returning token secrets."""
    account = _browser_account(request, db)
    records = (
        db.query(MCPToken).filter(MCPToken.account_id == account.id).order_by(MCPToken.id).all()
    )
    return [_token_response(record) for record in records]


@router.delete("/mcp-tokens/{token_id}", status_code=204)
def revoke_mcp_token(
    token_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Revoke own token; unknown/foreign IDs are indistinguishable."""
    account = _browser_account(request, db)
    record = (
        db.query(MCPToken)
        .filter(MCPToken.id == token_id, MCPToken.account_id == account.id)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="MCP token not found")
    record.revoked_at = datetime.now(UTC)
    db.commit()
