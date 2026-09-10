"""Focused tests for account-owned provider connections."""

import ipaddress
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from career_os.models.auth import Account
from career_os.schemas.provider_connections import (
    ProviderConnectionCreate,
    ProviderConnectionUpdate,
)
from career_os.services.provider_connections import (
    _request,
    create_connection,
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


def test_validate_target_returns_deterministic_public_ip():
    addresses = {ipaddress.ip_address("8.8.8.8"), ipaddress.ip_address("1.1.1.1")}
    with patch(
        "career_os.services.provider_connections._host_ips", return_value=addresses
    ):
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
