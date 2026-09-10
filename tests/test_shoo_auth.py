"""Shoo token, session, CSRF, ownership, and migration behavior."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from career_os.config import settings
from career_os.main import app
from career_os.models.auth import Account, AuthSession
from career_os.models.models import Application, Profile
from career_os.services import auth
from career_os.services.auth import account_for_claims, create_session, verify_shoo_token


def _claims(subject: str = "ps_test") -> dict:
    now = datetime.now(UTC)
    return {
        "iss": "https://shoo.dev",
        "aud": "origin:https://testserver",
        "sub": subject,
        "pairwise_sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "jti": f"jti-{subject}",
    }


def test_verify_shoo_token_checks_signature_issuer_audience_expiry_and_pairwise(monkeypatch):
    """Only valid ES256 Shoo token for configured origin passes."""
    key = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(_claims(), key, algorithm="ES256", headers={"kid": "key-1"})
    monkeypatch.setattr(
        auth,
        "_jwks_client",
        lambda _url: type(
            "Keys",
            (),
            {
                "get_signing_key_from_jwt": lambda self, _token: type(
                    "Key", (), {"key": key.public_key()}
                )()
            },
        )(),
    )

    decoded = verify_shoo_token(token, app_origin="https://testserver/path")
    assert decoded["pairwise_sub"] == "ps_test"
    assert decoded["sub"] == decoded["pairwise_sub"]

    with pytest.raises(auth.InvalidShooTokenError):
        verify_shoo_token(token, app_origin="https://other.example")
    assert settings.shoo_jwks_url.startswith("https://shoo.dev/")


def _account(db: Session, subject: str, profile_id: int) -> tuple[Account, Profile, str, str]:
    account = Account(pairwise_sub=subject)
    db.add(account)
    db.flush()
    profile = Profile(id=profile_id, account_id=account.id, name=f"User {profile_id}")
    db.add(profile)
    db.commit()
    token, csrf, _ = create_session(db, account)
    return account, profile, token, csrf


def _client(token: str, csrf: str) -> TestClient:
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(settings.session_cookie_name, token)
    client.cookies.set("kestrel_csrf", csrf)
    return client


def test_session_route_matrix_and_csrf(db_session: Session, monkeypatch):
    """Anonymous private API fails; valid session reads; mutation needs CSRF."""
    monkeypatch.setattr(settings, "shoo_auth_enabled", True)
    _, profile, token, csrf = _account(db_session, "ps_owner", 11)
    anonymous = TestClient(app, base_url="https://testserver")
    assert anonymous.get("/health").status_code == 200
    assert anonymous.get(f"/api/analytics?profile_id={profile.id}").status_code == 401

    owner = _client(token, csrf)
    assert owner.get(f"/api/applications?profile_id={profile.id}").status_code == 200
    blocked = owner.post(
        "/api/applications", json={"profile_id": profile.id, "company": "A", "role": "R"}
    )
    assert blocked.status_code == 403
    allowed = owner.post(
        "/api/applications",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": profile.id, "company": "A", "role": "R"},
    )
    assert allowed.status_code == 201


def test_two_accounts_cannot_read_or_write_each_others_records(db_session: Session, monkeypatch):
    """Authenticated account cannot select foreign profile for reads or writes."""
    monkeypatch.setattr(settings, "shoo_auth_enabled", True)
    _, profile_a, token_a, csrf_a = _account(db_session, "ps_a", 21)
    _, profile_b, token_b, csrf_b = _account(db_session, "ps_b", 22)
    app_a = Application(profile_id=profile_a.id, company="Owner A", role="Private")
    db_session.add(app_a)
    db_session.commit()
    a = _client(token_a, csrf_a)
    b = _client(token_b, csrf_b)

    assert a.get(f"/api/applications/{app_a.id}?profile_id={profile_a.id}").status_code == 200
    assert b.get(f"/api/applications/{app_a.id}?profile_id={profile_a.id}").status_code == 404
    response = b.patch(
        f"/api/applications/{app_a.id}?profile_id={profile_a.id}",
        headers={"X-CSRF-Token": csrf_b},
        json={"notes": "changed"},
    )
    assert response.status_code == 404
    db_session.refresh(app_a)
    assert app_a.notes is None

def test_hostile_origin_cannot_read_credentialed_private_response(
    db_session: Session, monkeypatch
):
    """Credentialed private GETs never expose data to an untrusted origin."""
    monkeypatch.setattr(settings, "shoo_auth_enabled", True)
    _, profile, token, csrf = _account(db_session, "ps_cors", 25)
    owner = _client(token, csrf)

    response = owner.get(
        f"/api/applications?profile_id={profile.id}",
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers

@pytest.mark.parametrize("content_type", ["application/merge-patch+json", "Application/JSON; charset=utf-8"])
def test_foreign_profile_body_rejected_for_all_json_media_types(
    db_session: Session, monkeypatch, content_type: str
):
    """Ownership gate inspects JSON bodies regardless of valid media-type spelling."""
    monkeypatch.setattr(settings, "shoo_auth_enabled", True)
    _, profile_a, token_a, csrf_a = _account(db_session, "ps_media_a", 23)
    _, profile_b, _, _ = _account(db_session, "ps_media_b", 24)
    owner = _client(token_a, csrf_a)

    response = owner.post(
        "/api/applications",
        headers={"X-CSRF-Token": csrf_a, "Content-Type": content_type},
        content=(
            f'{{"profile_id": {profile_b.id}, "company": "Foreign", "role": "Write"}}'
        ),
    )

    assert response.status_code == 404
    assert db_session.query(Application).filter(Application.profile_id == profile_b.id).count() == 0


def test_login_logout_expiry_and_legacy_claim(db_session: Session, monkeypatch):
    """Login sets secure cookies, logout revokes, expiry rejects, claim is explicit."""
    legacy = Profile(id=31, name="Legacy")
    db_session.add(legacy)
    db_session.commit()
    monkeypatch.setattr(settings, "shoo_auth_enabled", True)
    monkeypatch.setattr(settings, "shoo_claim_legacy_data", True)
    monkeypatch.setattr(
        "career_os.api.shoo_auth.verify_shoo_token", lambda *_args, **_kwargs: _claims("ps_legacy")
    )
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/auth/shoo/login", json={"id_token": "signed"})
    assert response.status_code == 200
    assert response.json()["profile_id"] == legacy.id
    assert "HttpOnly" in response.headers.get_list("set-cookie")[0]
    assert "Secure" in response.headers.get_list("set-cookie")[0]
    csrf = client.cookies.get("kestrel_csrf")
    logout = client.post("/api/auth/shoo/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200
    assert db_session.query(AuthSession).count() == 0

    account = db_session.query(Account).filter(Account.pairwise_sub == "ps_legacy").one()
    token, _, session = create_session(db_session, account)
    session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()
    expired = _client(token, "unused")
    assert expired.get("/api/profiles").status_code == 401
    assert db_session.query(AuthSession).count() == 0


def test_legacy_data_not_claimed_without_operator_opt_in(db_session: Session, monkeypatch):
    """Default first login preserves unowned data and creates separate profile."""
    legacy = Profile(id=41, name="Legacy")
    db_session.add(legacy)
    db_session.commit()
    monkeypatch.setattr(settings, "shoo_claim_legacy_data", False)

    account = account_for_claims(db_session, _claims("ps_new"))
    db_session.refresh(legacy)
    assert legacy.account_id is None
    assert len(account.profiles) == 1
    assert account.profiles[0].id != legacy.id
