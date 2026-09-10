"""Focused security checks for hosted MCP surface."""

import inspect
import json

import pytest

from career_os.mcp_server import (
    MCPTokenVerifier,
    _safe,
    archive_application,
    create_application,
    create_learning_resource,
    create_skill,
    discover_jobs,
    list_discoveries,
    list_learning_resources,
    list_pipeline,
    list_provider_connections,
    list_skills,
    settings_summary,
    select_provider,
    update_learning_resource,
    update_provider_connection,
    update_skill,
)


def test_safe_output_removes_credentials_recursively() -> None:
    value = _safe({"name": "agent", "api_key": "hidden", "nested": [{"secret": "x", "ok": 1}]})
    assert value == {"name": "agent", "nested": [{"ok": 1}]}


def test_write_tools_require_server_owned_context_and_destructive_confirmation() -> None:
    assert "profile_id" not in inspect.signature(create_application).parameters
    assert "profile_id" not in inspect.signature(list_pipeline).parameters
    assert "confirm" in inspect.signature(archive_application).parameters

def test_hosted_read_domains_have_no_caller_ownership_inputs() -> None:
    for tool in (
        list_discoveries,
        list_skills,
        list_learning_resources,
        settings_summary,
        list_provider_connections,
    ):
        assert "profile_id" not in inspect.signature(tool).parameters
        assert "account_id" not in inspect.signature(tool).parameters


def test_hosted_mutation_tools_derive_ownership_and_bound_writes() -> None:
    for tool in (
        discover_jobs,
        create_skill,
        update_skill,
        create_learning_resource,
        update_learning_resource,
        select_provider,
        update_provider_connection,
    ):
        params = inspect.signature(tool).parameters
        assert "profile_id" not in params
        assert "account_id" not in params
    assert "confirm" not in inspect.signature(select_provider).parameters

@pytest.mark.asyncio
async def test_verifier_rejects_profile_from_another_account(monkeypatch) -> None:
    class Query:
        def __init__(self, value):
            self.value = value

        def filter(self, *args):
            return self

        def first(self):
            return self.value

    class DB:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def query(self, model):
            from career_os.models.auth import MCPToken
            from career_os.models.models import Profile

            if model is MCPToken:
                return Query(
                    MCPToken(
                        id=1,
                        account_id=10,
                        profile_id=2,
                        token_hash="hash",
                        token_prefix="kst_",
                        name="test",
                        scopes="mcp:read",
                    )
                )
            if model is Profile:
                return Query(Profile(id=2, account_id=99, name="other"))
            raise AssertionError(model)

    monkeypatch.setattr("career_os.mcp_server._db", DB)
    monkeypatch.setattr("career_os.mcp_server.hashlib.sha256", lambda _: type("D", (), {"hexdigest": lambda self: "hash"})())
    assert await MCPTokenVerifier().verify_token("token") is None


def test_archive_without_confirmation_is_refused() -> None:
    # Authentication precedes destructive-action validation at tool boundary.
    with pytest.raises(PermissionError, match="Authentication required"):
        archive_application(42, confirm=False)
    safe = json.dumps(_safe({"token": "secret", "id": 42}))
    assert "secret" not in safe
    assert '"id": 42' in safe
