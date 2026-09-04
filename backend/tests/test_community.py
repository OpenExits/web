"""ADR-7 community layer: threads, confirmed-current, report-a-problem."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from openexits_panel.db import session as db_session
from openexits_panel.models import SiteConfirmation

SITE_ID = "01J9Y0AAAAAAAAAAAAAAAAAAAA"  # the seeded synthetic Héron site


def test_comment_thread_and_soft_delete(commons_app, contributor):
    client, headers = contributor
    r = client.post(f"/api/v1/sites/{SITE_ID}/comments", headers=headers,
                    json={"body": "Fil de discussion fictif — approche dégagée hier."})
    assert r.status_code == 201
    cid = r.get_json()["id"]

    community = commons_app.test_client().get(
        "/api/v1/public/sites/fr/pointe-du-heron/community").get_json()
    assert community["site_id"] == SITE_ID
    assert len(community["comments"]) == 1
    assert community["comments"][0]["handle"] == "test_user"

    assert client.delete(f"/api/v1/comments/{cid}", headers=headers).status_code == 200
    community = commons_app.test_client().get(
        "/api/v1/public/sites/fr/pointe-du-heron/community").get_json()
    assert community["comments"] == []  # gone from public view

    with commons_app.app_context():  # ...but survives as a soft-deleted row
        db = db_session()
        try:
            from openexits_panel.models import SiteComment
            row = db.get(SiteComment, cid)
            assert row is not None and row.deleted_at is not None
        finally:
            db.close()


def test_empty_comment_and_unknown_site_rejected(contributor):
    client, headers = contributor
    assert client.post(f"/api/v1/sites/{SITE_ID}/comments", headers=headers,
                       json={"body": "  "}).status_code == 422
    assert client.post("/api/v1/sites/01J9ZZZZZZZZZZZZZZZZZZZZZZ/comments",
                       headers=headers, json={"body": "x"}).status_code == 404


def test_confirm_upserts_and_rolling_window(commons_app, contributor):
    client, headers = contributor
    r1 = client.post(f"/api/v1/sites/{SITE_ID}/confirm", headers=headers)
    assert r1.status_code == 201
    assert r1.get_json()["confirmations_12mo"] == 1

    r2 = client.post(f"/api/v1/sites/{SITE_ID}/confirm", headers=headers)
    assert r2.get_json()["confirmations_12mo"] == 1  # updated, not duplicated

    # an old confirmation from another user falls outside the rolling window
    old_date = (datetime.now(timezone.utc) - timedelta(days=400)).strftime("%Y-%m-%d")
    with commons_app.app_context():
        db = db_session()
        try:
            from openexits_panel.models import User
            ghost = User(handle="ghost", email="g@example.invalid", password_hash="x")
            db.add(ghost)
            db.flush()
            db.add(SiteConfirmation(site_id=SITE_ID, user_id=ghost.id,
                                    confirmed_on=old_date))
            db.commit()
        finally:
            db.close()

    community = commons_app.test_client().get(
        "/api/v1/public/sites/fr/pointe-du-heron/community").get_json()
    assert community["confirmations"]["confirmations_12mo"] == 1  # old one excluded
    assert community["confirmations"]["last_confirmed_on"] >= old_date


def test_report_requires_category(contributor):
    client, headers = contributor
    bad = client.post(f"/api/v1/sites/{SITE_ID}/report", headers=headers,
                      json={"body": "quelque chose ne va pas"})
    assert bad.status_code == 422
    assert "categories" in bad.get_json()

    ok = client.post(f"/api/v1/sites/{SITE_ID}/report", headers=headers,
                     json={"category": "measurement", "body": "rockdrop semble faux"})
    assert ok.status_code == 201
    assert ok.get_json()["status"] == "open"
