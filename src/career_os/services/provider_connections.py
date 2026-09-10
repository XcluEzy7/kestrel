"""Secure account-owned OpenAI-compatible provider connections."""

import ipaddress
import json
import logging
import os
import socket
from urllib.parse import urlsplit, urlunsplit

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from career_os.config import settings
from career_os.models.auth import Account, ProviderConnection
from career_os.schemas.provider_connections import (
    ProviderCompletionResponse,
    ProviderConnectionCreate,
    ProviderConnectionResponse,
    ProviderConnectionUpdate,
    ProviderModelsResponse,
    ProviderTestResponse,
)

logger = logging.getLogger(__name__)
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
_METADATA_HOSTS = frozenset({"metadata.google.internal", "metadata", "instance-data.ec2.internal"})
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def local_loopback_allowed() -> bool:
    """Return whether operator explicitly enabled local provider loopback."""
    return settings.debug or os.getenv(
        "CAREER_OS_ALLOW_LOCAL_PROVIDER_LOOPBACK", ""
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def ensure_loopback_policy(url: str) -> None:
    """Reject localhost provider targets unless local/debug policy is enabled."""
    hostname = (urlsplit(url).hostname or "").lower()
    if hostname in _LOCAL_HOSTS and not local_loopback_allowed():
        raise ValueError("Local provider loopback is disabled outside local/debug mode")


def normalize_base_url(value: str) -> str:
    """Normalize provider URL to an origin/path ending in ``/v1``."""
    raw = value.strip()
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("base_url must use http or https and include a hostname")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("base_url cannot contain credentials, query, or fragment")
    path = parsed.path.rstrip("/")
    if not path or path == "/v1":
        path = "/v1"
    elif not path.endswith("/v1"):
        path += "/v1"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, path, "", ""))


def _fernet() -> Fernet:
    key = settings.cache_encryption_key
    if not key:
        key_path = settings.data_dir / ".provider_key"
        if key_path.exists():
            key = key_path.read_text(encoding="utf-8").strip()
        else:
            key = Fernet.generate_key().decode()
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_text(key, encoding="utf-8")
            key_path.chmod(0o600)
    return Fernet(key.encode())


def _encrypt(value: str | None) -> str | None:
    return _fernet().encrypt(value.encode()).decode() if value else None


def _decrypt(value: str | None) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        raise ValueError("Stored provider credential cannot be decrypted") from None


def _response(row: ProviderConnection) -> ProviderConnectionResponse:
    return ProviderConnectionResponse(
        id=row.id,
        display_name=row.display_name,
        provider_type=row.provider_type,
        base_url=row.base_url,
        model=row.model,
        enabled=row.enabled,
        api_key_configured=bool(row.api_key_encrypted),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_connections(db: Session, account: Account) -> list[ProviderConnectionResponse]:
    rows = db.query(ProviderConnection).filter(ProviderConnection.account_id == account.id).all()
    return [_response(row) for row in rows]


def get_connection(db: Session, account: Account, connection_id: int) -> ProviderConnection:
    row = (
        db.query(ProviderConnection)
        .filter(ProviderConnection.id == connection_id, ProviderConnection.account_id == account.id)
        .first()
    )
    if row is None:
        raise LookupError("Provider connection not found")
    return row


def create_connection(db: Session, account: Account, payload: ProviderConnectionCreate):
    row = ProviderConnection(
        account_id=account.id,
        display_name=payload.display_name.strip(),
        provider_type=payload.provider_type.strip().lower(),
        base_url=normalize_base_url(payload.base_url),
        api_key_encrypted=_encrypt(payload.api_key),
        model=payload.model.strip(),
        enabled=payload.enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _response(row)


def update_connection(db: Session, row: ProviderConnection, payload: ProviderConnectionUpdate):
    values = payload.model_dump(exclude_unset=True)
    if "display_name" in values:
        row.display_name = values["display_name"].strip()
    if "provider_type" in values:
        row.provider_type = values["provider_type"].strip().lower()
    if "base_url" in values:
        row.base_url = normalize_base_url(values["base_url"])
    if "model" in values:
        row.model = values["model"].strip()
    if "enabled" in values:
        row.enabled = values["enabled"]
    if "api_key" in values and values["api_key"]:
        row.api_key_encrypted = _encrypt(values["api_key"])
    db.commit()
    db.refresh(row)
    return _response(row)


def _host_ips(hostname: str) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("Provider hostname could not be resolved") from exc
    return {ipaddress.ip_address(info[4][0]) for info in infos}


def validate_target(url: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Validate target and return public address used for its connection."""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host in _METADATA_HOSTS:
        raise ValueError("Provider target is not allowed")
    ips = _host_ips(host)
    for ip in ips:
        if not ip.is_global or ip.is_multicast:
            raise ValueError("Provider target resolves to a non-public address")
    if not ips:
        raise ValueError("Provider hostname could not be resolved")
    # Resolve once, then use this exact address for the request. Sorting keeps
    # behavior deterministic when DNS returns multiple public addresses.
    return min(ips, key=lambda ip: (ip.version, int(ip)))


async def _request(row: ProviderConnection, method: str, suffix: str, payload: dict | None = None):
    url = f"{row.base_url.rstrip('/')}/{suffix.lstrip('/')}"
    parsed = urlsplit(url)
    local_ollama = (
        row.provider_type in {"ollama", "ollama_local"}
        and (parsed.hostname or "").lower() in _LOCAL_HOSTS
    )
    if local_ollama:
        ensure_loopback_policy(url)
    validated_ip = None if local_ollama else validate_target(url)
    headers = {"Accept": "application/json"}
    request_url: str | httpx.URL = url
    extensions: dict[str, str] = {}
    if validated_ip is not None:
        request_url = httpx.URL(url).copy_with(host=str(validated_ip))
        # Keep HTTP Host and TLS SNI bound to configured hostname while TCP
        # connects to validated_ip. This also preserves certificate checking.
        headers["Host"] = parsed.netloc
        extensions["sni_hostname"] = parsed.hostname or ""
    api_key = _decrypt(row.api_key_encrypted)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client:
        async with client.stream(
            method, request_url, headers=headers, json=payload, extensions=extensions
        ) as response:
            if response.is_redirect:
                raise ValueError("Provider redirects are not allowed")
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > _MAX_RESPONSE_BYTES:
                    raise ValueError("Provider response exceeds size limit")
                chunks.append(chunk)
            body = b"".join(chunks)
            response.raise_for_status()
            return json.loads(body)


async def discover_models(row: ProviderConnection) -> ProviderModelsResponse:
    data = await _request(row, "GET", "models")
    models = [
        str(item["id"])
        for item in data.get("data", [])
        if isinstance(item, dict) and item.get("id")
    ]
    return ProviderModelsResponse(models=models)


async def test_connection(row: ProviderConnection) -> ProviderTestResponse:
    try:
        discovered = await discover_models(row)
        return ProviderTestResponse(
            success=True, message="Connection test passed.", models=discovered.models
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        logger.warning("Provider connection test failed for id=%s: %s", row.id, type(exc).__name__)
        return ProviderTestResponse(success=False, message="Provider connection test failed.")


async def complete(
    row: ProviderConnection, prompt: str, model: str | None = None
) -> ProviderCompletionResponse:
    if not row.enabled:
        raise ValueError("Provider connection is disabled")
    data = await _request(
        row,
        "POST",
        "chat/completions",
        {"model": model or row.model, "messages": [{"role": "user", "content": prompt}]},
    )
    content = data["choices"][0]["message"]["content"]
    return ProviderCompletionResponse(content=content, model=data.get("model", model or row.model))
