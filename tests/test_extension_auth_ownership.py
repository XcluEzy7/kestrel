"""Account-bound browser-extension authentication tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from career_os.config import settings
from career_os.main import app
from career_os.models.auth import Account
from career_os.models.models import Profile
from career_os.services import extension_pairing


def test_extension_token_carries_account_without_browser_session(tmp_path, monkeypatch):
    """Dedicated token stays cookie-less while retaining account owner."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "extension_token_secret", "test-extension-secret")
    token = extension_pairing.mint_extension_token(17)

    assert extension_pairing.extension_token_account(token) == 17
    assert extension_pairing.verify_extension_token(token) is True


def test_pairing_binds_token_to_selected_account(db_session: Session, tmp_path, monkeypatch):
    """Pair code yields token whose account cannot change client-side."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "extension_token_secret", "test-extension-secret")
    account = Account(pairwise_sub="ps_extension")
    db_session.add(account)
    db_session.flush()
    db_session.add(Profile(account_id=account.id, name="Extension owner"))
    db_session.commit()
    code = extension_pairing.mint_pairing_code(account.id)

    response = TestClient(app).post("/api/extension/pair", json={"pairing_code": code})
    assert response.status_code == 200
    assert extension_pairing.extension_token_account(response.json()["token"]) == account.id

def test_shoo_rejects_unbound_extension_token_and_pairing(
    tmp_path, monkeypatch
):
    """Shoo mode never accepts or mints extension credentials without an owner."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "extension_token_secret", "test-extension-secret")
    monkeypatch.setattr(settings, "shoo_auth_enabled", False)
    unbound_token = extension_pairing.mint_extension_token()
    pairing_code = extension_pairing.mint_pairing_code()

    monkeypatch.setattr(settings, "shoo_auth_enabled", True)
    client = TestClient(app)
    unbound_response = client.get(
        "/api/extension/status",
        headers={"Authorization": f"Bearer {unbound_token}"},
    )
    assert unbound_response.status_code == 401

    bound_response = client.get(
        "/api/extension/status",
        headers={"Authorization": f"Bearer {extension_pairing.mint_extension_token(17)}"},
    )
    assert bound_response.status_code == 200

    pair_response = client.post("/api/extension/pair", json={"pairing_code": pairing_code})
    assert pair_response.status_code == 401
