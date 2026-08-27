"""Auth, roles, CSRF, terms versioning (Phase 3 verification)."""
from __future__ import annotations

from conftest import csrf_of, register

from openexit_panel.db import session as db_session
from openexit_panel.models import User


def test_register_login_me_logout(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user"]["handle"] == "test_user"
    assert body["user"]["role"] == "user"
    assert body["user"]["terms_accepted"] is False
    csrf = csrf_of(resp)

    me = client.get("/api/v1/auth/me").get_json()
    assert me["user"]["handle"] == "test_user"

    out = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert out.status_code == 200
    assert client.get("/api/v1/auth/me").get_json()["user"] is None

    back = client.post("/api/v1/auth/login",
                       json={"email": "t@example.invalid", "password": "longenough123"})
    assert back.status_code == 200


def test_bad_credentials_and_validation(client):
    assert register(client, password="short").status_code == 422
    assert register(client, handle="BAD HANDLE!").status_code == 422
    register(client)
    dup = register(client, email="other@example.invalid")
    assert dup.status_code == 409
    bad = client.post("/api/v1/auth/login",
                      json={"email": "t@example.invalid", "password": "wrongwrongwrong"})
    assert bad.status_code == 401


def test_csrf_required_on_mutations(client):
    register(client)
    no_token = client.post("/api/v1/auth/logout")
    assert no_token.status_code == 403
    assert no_token.get_json()["error"] == "csrf"


def test_password_stored_as_argon2_hash(app, client):
    register(client)
    with app.app_context():
        db = db_session()
        try:
            user = db.query(User).one()
            assert user.password_hash.startswith("$argon2id$")
            assert "longenough123" not in user.password_hash
        finally:
            db.close()


def test_role_guard(app, client):
    resp = register(client)
    csrf = csrf_of(resp)
    denied = client.get("/api/v1/_test/mod-only")
    assert denied.status_code == 403

    with app.app_context():
        db = db_session()
        try:
            user = db.query(User).one()
            user.role = "moderator"
            db.commit()
        finally:
            db.close()
    allowed = client.get("/api/v1/_test/mod-only", headers={"X-CSRF-Token": csrf})
    assert allowed.status_code == 200


def test_terms_acceptance_and_version_bump_blocks(app, client):
    resp = register(client)
    csrf = csrf_of(resp)
    headers = {"X-CSRF-Token": csrf}

    # blocked before acceptance
    blocked = client.post("/api/v1/_test/needs-terms", headers=headers)
    assert blocked.status_code == 428
    assert blocked.get_json()["error"] == "terms_outdated"

    # wrong version refused
    wrong = client.post("/api/v1/terms/accept", headers=headers,
                        json={"terms_version": "contributor-terms-1999-01"})
    assert wrong.status_code == 422

    # accept current -> unblocked
    ok = client.post("/api/v1/terms/accept", headers=headers,
                     json={"terms_version": "contributor-terms-2026-08"})
    assert ok.status_code == 201
    assert client.post("/api/v1/_test/needs-terms", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/me").get_json()["user"]["terms_accepted"] is True

    # simulate a terms bump: blocked again until re-acceptance
    app.config["TERMS_VERSION"] = "contributor-terms-2027-01"
    bumped = client.post("/api/v1/_test/needs-terms", headers=headers)
    assert bumped.status_code == 428
    re_ok = client.post("/api/v1/terms/accept", headers=headers,
                        json={"terms_version": "contributor-terms-2027-01"})
    assert re_ok.status_code == 201
    assert client.post("/api/v1/_test/needs-terms", headers=headers).status_code == 200
