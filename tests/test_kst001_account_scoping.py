"""KST-001 account ownership regressions."""

import pytest

from career_os.database import get_db
from career_os.dependencies import current_account
from career_os.main import app
from career_os.models.auth import Account
from career_os.models.models import Profile
from career_os.services.integrations import get_integration


@pytest.fixture
def accounts(db_session):
    first = Account(pairwise_sub="kst001-a")
    second = Account(pairwise_sub="kst001-b")
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add_all([
        Profile(account_id=first.id, name="Account A"),
        Profile(account_id=second.id, name="Account B"),
    ])
    db_session.commit()
    return first, second


def _as_account(account):
    app.dependency_overrides[current_account] = lambda: account


def test_profile_routes_hide_foreign_account(client, accounts):
    first, second = accounts
    _as_account(first)
    profile_id = client.get("/api/profiles").json()["profiles"][0]["id"]
    _as_account(second)

    assert client.get(f"/api/profiles/{profile_id}").status_code == 404
    assert client.patch(f"/api/profiles/{profile_id}", json={"name": "stolen"}).status_code == 404
    assert client.delete(f"/api/profiles/{profile_id}").status_code == 404
    app.dependency_overrides.pop(current_account, None)


def test_integration_config_isolated_by_account(db_session, accounts):
    first, second = accounts
    from career_os.schemas.integrations import IntegrationConfigUpdate
    from career_os.services.integrations import update_integration

    update_integration(
        db_session,
        "ai_providers",
        IntegrationConfigUpdate(credentials={"openrouter_api_key": "account-a"}),
        account=first,
    )
    assert get_integration(db_session, "ai_providers", account=second).credentials_set[
        "openrouter_api_key"
    ] is False
    assert get_integration(db_session, "ai_providers", account=first).credentials_set[
        "openrouter_api_key"
    ] is True
