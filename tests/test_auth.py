"""Tests for API key auth middleware (#22)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from career_os.middleware import APIKeyAuthMiddleware


def _make_app(*, auth_enabled: bool, auth_api_key: str = "test-secret") -> FastAPI:
    """Create a minimal FastAPI app with auth middleware for testing."""
    test_app = FastAPI()
    test_app.add_middleware(
        APIKeyAuthMiddleware,
        auth_enabled=auth_enabled,
        auth_api_key=auth_api_key,
    )

    @test_app.get("/health")
    async def health():
        return {"status": "ok"}

    @test_app.get("/api/profiles")
    async def profiles():
        return {"profiles": [], "count": 0}

    return test_app


class TestAuthDisabled:
    """When auth_enabled=False, all requests pass through."""

    def test_no_header_passes(self):
        client = TestClient(_make_app(auth_enabled=False))
        resp = client.get("/api/profiles")
        assert resp.status_code == 200

    def test_bad_key_ignored(self):
        client = TestClient(_make_app(auth_enabled=False))
        resp = client.get(
            "/api/profiles",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 200


class TestAuthEnabled:
    """When auth_enabled=True, require valid Bearer token."""

    def test_no_header_401(self):
        client = TestClient(_make_app(auth_enabled=True))
        resp = client.get("/api/profiles")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Unauthorized"

    def test_wrong_key_401(self):
        client = TestClient(_make_app(auth_enabled=True))
        resp = client.get(
            "/api/profiles",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 401

    def test_correct_key_passes(self):
        client = TestClient(_make_app(auth_enabled=True))
        resp = client.get(
            "/api/profiles",
            headers={"Authorization": "Bearer test-secret"},
        )
        assert resp.status_code == 200

    def test_health_always_passes(self):
        client = TestClient(_make_app(auth_enabled=True))
        resp = client.get("/health")
        assert resp.status_code == 200

    @pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
    def test_api_documentation_is_not_public(self, path):
        client = TestClient(_make_app(auth_enabled=True))
        resp = client.get(path)
        assert resp.status_code == 401

    def test_missing_bearer_prefix_401(self):
        client = TestClient(_make_app(auth_enabled=True))
        resp = client.get(
            "/api/profiles",
            headers={"Authorization": "test-secret"},
        )
        assert resp.status_code == 401


class TestStartupValidation:
    """Settings validation at startup."""

    def test_auth_enabled_empty_key_raises(self):
        from career_os.config import Settings

        with pytest.raises(ValueError, match="AUTH_API_KEY is required"):
            Settings(
                auth_enabled=True,
                auth_api_key="",
                database_url="sqlite:///test.db",
            )

    def test_auth_enabled_with_key_ok(self):
        from career_os.config import Settings

        s = Settings(
            auth_enabled=True,
            auth_api_key="my-secret",
            database_url="sqlite:///test.db",
        )
        assert s.auth_enabled is True
        assert s.auth_api_key == "my-secret"

    def test_production_mode_requires_shoo_auth(self):
        from career_os.config import Settings

        with pytest.raises(ValueError, match="SHOO_AUTH_ENABLED is required"):
            Settings(production_mode=True, shoo_auth_enabled=False)

    def test_production_mode_with_shoo_auth_is_valid(self):
        from career_os.config import Settings

        s = Settings(production_mode=True, shoo_auth_enabled=True)
        assert s.production_mode is True
        assert s.shoo_auth_enabled is True

    def test_local_mode_keeps_shoo_auth_optional(self):
        from career_os.config import Settings

        s = Settings(production_mode=False, shoo_auth_enabled=False)
        assert s.production_mode is False
        assert s.shoo_auth_enabled is False

    def test_wildcard_frontend_url_rejected(self):
        from career_os.config import Settings

        with pytest.raises(ValueError, match="FRONTEND_URL must be an explicit origin"):
            Settings(frontend_url="*")
