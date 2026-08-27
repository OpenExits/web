from __future__ import annotations

import pytest

from openexit_panel.app import create_app
from openexit_panel.config import Config


class TestConfig(Config):
    TESTING = True
    DB_URL = "sqlite://"          # in-memory, per test app
    SECRET_KEY = "test-secret"
    TERMS_VERSION = "contributor-terms-2026-08"


@pytest.fixture()
def app():
    app = create_app(TestConfig, create_tables=True)
    # test-only probe endpoints (must be registered before the first request)
    from openexit_panel.auth import require_auth, require_current_terms

    @app.post("/api/v1/_test/needs-terms")
    @require_auth()
    @require_current_terms
    def _needs_terms():
        return {"ok": True}

    @app.get("/api/v1/_test/mod-only")
    @require_auth(role="moderator")
    def _mod_only():
        return {"ok": True}

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, handle="test_user", email="t@example.invalid",
             password="longenough123", locale="en"):
    resp = client.post("/api/v1/auth/register", json={
        "handle": handle, "email": email, "password": password, "locale": locale,
    })
    return resp


def csrf_of(resp) -> str:
    return resp.get_json()["csrf"]
