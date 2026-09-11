"""Focused tests for account-owned provider connections."""

import ipaddress
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from career_os.config import settings
from career_os.main import app
from career_os.models.auth import Account, ProviderConnection
from career_os.schemas.provider_connections import (
    ProviderConnectionCreate,
    ProviderConnectionUpdate,
    ProviderDiscoveryRequest,
    ProviderModelsResponse,
)
from career_os.services.auth import create_session
from career_os.services.provider_connections import (
    _request,
    complete,
    create_connection,
    discover_draft_models,
    ensure_loopback_policy,
    normalize_base_url,
    validate_target,
)


def test_loopback_provider_rejected_without_explicit_local_policy(monkeypatch):
    monkeypatch.setattr("career_os.services.provider_connections.settings.debug", False)
    monkeypatch.delenv("CAREER_OS_ALLOW_LOCAL_PROVIDER_LOOPBACK", raising=False)
    with pytest.raises(ValueError, match="loopback"):
        ensure_loopback_policy("http://127.0.0.1:11434/v1/models")


def test_loopback_provider_allowed_with_debug_policy(monkeypatch):
    monkeypatch.setattr("career_os.services.provider_connections.settings.debug", True)
    ensure_loopback_policy("http://localhost:11434/v1/models")


def _account(db: Session, subject: str) -> Account:
    account = Account(
        pairwise_sub=subject, created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def _session_client(db: Session, account: Account) -> TestClient:
    token, csrf, _ = create_session(db, account)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(settings.session_cookie_name, token)
    client.cookies.set("kestrel_csrf", csrf)
    client.headers.update({"X-CSRF-Token": csrf})
    return client


def test_normalize_base_url_adds_v1_and_rejects_url_credentials():
    assert normalize_base_url(" HTTPS://example.com/ ") == "https://example.com/v1"
    assert normalize_base_url("https://example.com/openai/v1/") == "https://example.com/openai/v1"
    with pytest.raises(ValueError, match="credentials"):
        normalize_base_url("https://user:pass@example.com/v1")


def test_validate_target_rejects_private_and_metadata_hosts():
    with pytest.raises(ValueError):
        with patch(
            "career_os.services.provider_connections._host_ips",
            return_value={ipaddress.ip_address("10.0.0.2")},
        ):
            validate_target("https://provider.example/v1/models")
    with pytest.raises(ValueError, match="not allowed"):
        validate_target("https://metadata.google.internal/v1/models")


@pytest.mark.parametrize("address", ["100.64.0.1", "100.100.100.200", "224.0.0.1"])
def test_validate_target_rejects_non_public_special_addresses(address):
    with pytest.raises(ValueError, match="non-public"):
        with patch(
            "career_os.services.provider_connections._host_ips",
            return_value={ipaddress.ip_address(address)},
        ):
            validate_target("https://provider.example/v1/models")


def test_validate_target_returns_deterministic_public_ip():
    addresses = {ipaddress.ip_address("8.8.8.8"), ipaddress.ip_address("1.1.1.1")}
    with patch("career_os.services.provider_connections._host_ips", return_value=addresses):
        assert validate_target("https://provider.example/v1/models") == ipaddress.ip_address(
            "1.1.1.1"
        )


def test_connection_owns_account_and_stores_encrypted_key(db_session: Session):
    owner = _account(db_session, "provider-owner")
    other = _account(db_session, "provider-other")
    row = create_connection(
        db_session,
        owner,
        ProviderConnectionCreate(
            display_name="Cloud",
            provider_type="ollama_cloud",
            base_url="https://ollama.com/v1",
            api_key="OLLAMA_API_KEY",
            model="llama3.3",
        ),
    )
    assert row.base_url == "https://ollama.com/v1"
    assert row.api_key_configured is True
    raw = db_session.execute(
        __import__("sqlalchemy").text(
            "SELECT api_key_encrypted FROM provider_connections WHERE id=:id"
        ),
        {"id": row.id},
    ).scalar_one()
    assert "OLLAMA_API_KEY" not in raw
    from career_os.services.provider_connections import get_connection, update_connection

    with pytest.raises(LookupError):
        get_connection(db_session, other, row.id)
    updated = update_connection(
        db_session,
        row and get_connection(db_session, owner, row.id),
        ProviderConnectionUpdate(enabled=False),
    )
    assert updated.enabled is False


def test_factory_selects_enabled_connection_for_account(db_session: Session):
    from career_os.ai.factory import AccountProvider, get_ai_provider

    owner = _account(db_session, "factory-owner")
    create_connection(
        db_session,
        owner,
        ProviderConnectionCreate(
            display_name="Account model",
            base_url="https://provider.example/v1",
            model="account-model",
        ),
    )
    provider = get_ai_provider(db=db_session, account=owner)
    assert isinstance(provider, AccountProvider)
    assert provider.connection.model == "account-model"


def test_create_endpoint_discovers_and_persists_omitted_model(db_session: Session, monkeypatch):
    """Omitted model is discovered before the connection is returned."""
    monkeypatch.setattr(settings, "shoo_auth_enabled", True)
    owner = _account(db_session, "provider-endpoint-owner")
    client = _session_client(db_session, owner)

    with patch(
        "career_os.api.provider_connections.discover_models",
        new=AsyncMock(return_value=ProviderModelsResponse(models=["discovered-model"])),
    ) as discover:
        response = client.post(
            "/api/provider-connections",
            json={
                "display_name": "Endpoint provider",
                "base_url": "https://provider.example/v1",
            },
        )

    assert response.status_code == 201
    assert response.json()["model"] == "discovered-model"
    discover.assert_awaited_once()
    assert db_session.query(ProviderConnection).one().model == "discovered-model"


def test_create_endpoint_rolls_back_connection_when_discovery_fails(
    db_session: Session, monkeypatch
):
    """Failed discovery does not leave an unusable saved connection behind."""
    monkeypatch.setattr(settings, "shoo_auth_enabled", True)
    owner = _account(db_session, "provider-endpoint-failure")
    client = _session_client(db_session, owner)

    with patch(
        "career_os.api.provider_connections.discover_models",
        new=AsyncMock(side_effect=ValueError("No usable provider model found")),
    ):
        response = client.post(
            "/api/provider-connections",
            json={
                "display_name": "Unavailable provider",
                "base_url": "https://provider.example/v1",
            },
        )

    assert response.status_code == 502
    assert db_session.query(ProviderConnection).count() == 0


@pytest.mark.asyncio
async def test_draft_discovery_uses_normalized_target_and_encrypted_key():
    payload = ProviderDiscoveryRequest(
        provider_type="ollama_cloud", base_url="https://ollama.com", api_key="draft-secret"
    )
    with patch(
        "career_os.services.provider_connections._request",
        new=AsyncMock(return_value={"data": [{"id": "cloud-model"}]}),
    ) as request:
        result = await discover_draft_models(payload)
    assert result.models == ["cloud-model"]
    row = request.call_args.args[0]
    assert row.base_url == "https://ollama.com/v1"
    assert row.api_key_encrypted != "draft-secret"


@pytest.mark.asyncio
async def test_completion_discovers_default_but_explicit_model_wins():
    from career_os.models.auth import ProviderConnection

    row = ProviderConnection(
        id=1,
        account_id=1,
        display_name="Test",
        provider_type="openai_compatible",
        base_url="https://provider.example/v1",
        model=None,
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        api_key_encrypted=None,
    )
    with patch(
        "career_os.services.provider_connections._request",
        new=AsyncMock(
            side_effect=[
                {"data": [{"id": "discovered-model"}]},
                {"choices": [{"message": {"content": "ok"}}]},
                {"choices": [{"message": {"content": "override"}}], "model": "override-model"},
            ]
        ),
    ) as request:
        discovered = await complete(row, "hello")
        explicit = await complete(row, "hello", "override-model")
    assert discovered.model == "discovered-model"
    assert explicit.model == "override-model"
    assert request.call_args_list[1].args[3]["model"] == "discovered-model"
    assert request.call_args_list[2].args[3]["model"] == "override-model"


@pytest.mark.asyncio
async def test_completion_rejects_empty_discovery():
    from career_os.models.auth import ProviderConnection

    row = ProviderConnection(
        id=1,
        account_id=1,
        display_name="Test",
        provider_type="ollama_local",
        base_url="http://localhost:11434/v1",
        model=None,
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        api_key_encrypted=None,
    )
    with patch(
        "career_os.services.provider_connections._request",
        new=AsyncMock(return_value={"data": []}),
    ):
        with pytest.raises(ValueError, match="usable provider model"):
            await complete(row, "hello")


@pytest.mark.asyncio
async def test_request_sends_bearer_key_and_rejects_redirect():
    from career_os.models.auth import ProviderConnection

    row = ProviderConnection(
        id=1,
        account_id=1,
        display_name="Test",
        provider_type="openai_compatible",
        base_url="https://provider.example/v1",
        api_key_encrypted=None,
        model="model",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    response = type(
        "Response",
        (),
        {
            "is_redirect": False,
            "aiter_bytes": lambda self: _chunks(),
            "__aenter__": lambda self: self,
            "__aexit__": lambda self, *args: False,
            "raise_for_status": lambda self: None,
            "json": lambda self: {"data": []},
        },
    )()

    async def _chunks():
        yield b'{"data": []}'

    client = MagicMock()
    stream_context = AsyncMock()
    stream_context.__aenter__.return_value = response
    stream_context.__aexit__.return_value = False
    client.stream.return_value = stream_context
    context = AsyncMock()
    context.__aenter__.return_value = client
    context.__aexit__.return_value = False
    with (
        patch(
            "career_os.services.provider_connections.validate_target",
            return_value=ipaddress.ip_address("8.8.8.8"),
        ),
        patch("httpx.AsyncClient", return_value=context),
    ):
        await _request(row, "GET", "models")
    client.stream.assert_called_once()
    request = client.stream.call_args.args
    assert str(request[1]) == "https://8.8.8.8/v1/models"
    assert client.stream.call_args.kwargs["headers"]["Host"] == "provider.example"
    assert client.stream.call_args.kwargs["extensions"] == {"sni_hostname": "provider.example"}

    response.is_redirect = True
    with patch(
        "career_os.services.provider_connections.validate_target",
        return_value=ipaddress.ip_address("8.8.8.8"),
    ):
        with patch("httpx.AsyncClient", return_value=context):
            with pytest.raises(ValueError, match="redirects are not allowed"):
                await _request(row, "GET", "models")
