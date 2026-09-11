"""Shoo OIDC verification and account-owned session services."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from sqlalchemy.orm import Session

from career_os.config import settings
from career_os.models.auth import Account, AuthBatch, AuthSession
from career_os.models.models import Profile

SHOO_ISSUER = "https://shoo.dev"


class InvalidShooTokenError(ValueError):
    """Raised when a Shoo token fails verification."""


def expected_audience(app_origin: str) -> str:
    """Build Shoo audience from trusted deployment origin."""
    parsed = urlsplit(app_origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("SHOO_APP_ORIGIN must be an absolute HTTP(S) origin")
    return f"origin:{parsed.scheme}://{parsed.netloc}"


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> jwt.PyJWKClient:
    """Return cached rotating-key client for configured Shoo JWKS URL."""
    return jwt.PyJWKClient(url, cache_keys=True, timeout=10)


def verify_shoo_token(token: str, *, app_origin: str) -> dict:
    """Verify Shoo ES256 signature and required identity claims."""
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "ES256" or not header.get("kid"):
            raise InvalidShooTokenError("Unsupported Shoo token header")
        key = _jwks_client(settings.shoo_jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key=key,
            algorithms=["ES256"],
            issuer=SHOO_ISSUER,
            audience=expected_audience(app_origin),
            options={"require": ["iss", "aud", "sub", "pairwise_sub", "iat", "exp", "jti"]},
            leeway=5,
        )
    except (jwt.PyJWTError, InvalidShooTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidShooTokenError("Invalid Shoo identity token") from exc
    pairwise_sub = claims.get("pairwise_sub")
    if not isinstance(pairwise_sub, str) or not pairwise_sub:
        raise InvalidShooTokenError("Shoo token missing pairwise_sub")
    if claims.get("sub") != pairwise_sub:
        raise InvalidShooTokenError("Shoo token subject mismatch")
    return claims


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_session(db: Session, account: Account) -> tuple[str, str, AuthSession]:
    """Create opaque browser session and CSRF secret; persist hashes only."""
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    session = AuthSession(
        account=account,
        token_hash=_hash(token),
        csrf_hash=_hash(csrf),
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.session_ttl_seconds),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return token, csrf, session


def get_session(db: Session, token: str | None) -> AuthSession | None:
    """Resolve non-expired opaque token by hash."""
    if not token:
        return None
    session = db.query(AuthSession).filter(AuthSession.token_hash == _hash(token)).first()
    if session is None:
        return None
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        db.delete(session)
        db.commit()
        return None
    return session


def csrf_valid(session: AuthSession, value: str | None) -> bool:
    """Check CSRF token against stored hash using timing-safe comparison."""
    return bool(value) and secrets.compare_digest(session.csrf_hash, _hash(value))


def account_for_claims(
    db: Session, claims: dict, *, claim_legacy: bool | None = None
) -> Account:
    """Find/create account and optionally claim unowned legacy profiles.

    ``claim_legacy`` defaults to the operator setting. Callers creating
    synthetic identities must pass ``False`` so they cannot claim legacy data.
    """
    pairwise_sub = claims["pairwise_sub"]
    account = db.query(Account).filter(Account.pairwise_sub == pairwise_sub).first()
    if account is not None:
        return account

    account = Account(pairwise_sub=pairwise_sub)
    db.add(account)
    db.flush()
    legacy_profiles = db.query(Profile).filter(Profile.account_id.is_(None)).all()
    if (settings.shoo_claim_legacy_data if claim_legacy is None else claim_legacy) and legacy_profiles:
        for profile in legacy_profiles:
            profile.account_id = account.id
    else:
        db.add(
            Profile(
                account_id=account.id,
                name=claims.get("name") or "Kestrel User",
                email=claims.get("email"),
            )
        )
    db.commit()
    db.refresh(account)
    return account


def default_profile(account: Account) -> Profile:
    """Return deterministic account profile used by current single-profile UI."""
    profile = min(account.profiles, key=lambda value: value.id, default=None)
    if profile is None:
        raise RuntimeError("Authenticated account has no profile")
    return profile


def create_batch_mapping(
    db: Session, account: Account, profile: Profile, provider: str, provider_batch_id: str
) -> AuthBatch:
    """Persist opaque account-owned mapping for remote provider batch ID."""
    batch = AuthBatch(
        public_id=secrets.token_urlsafe(24),
        account_id=account.id,
        profile_id=profile.id,
        provider=provider,
        provider_batch_id=provider_batch_id,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def owned_batch(db: Session, account: Account, public_id: str) -> AuthBatch | None:
    """Return batch mapping only for authenticated owner."""
    return (
        db.query(AuthBatch)
        .filter(AuthBatch.public_id == public_id, AuthBatch.account_id == account.id)
        .first()
    )


def session_cookie_kwargs() -> dict:
    """Return secure browser cookie settings."""
    return {
        "httponly": True,
        "secure": settings.session_cookie_secure,
        "samesite": "lax",
        "max_age": settings.session_ttl_seconds,
        "path": "/",
    }
