"""Contributor pipeline: validate, nearby, submit, flags, lifecycle."""
from __future__ import annotations

from conftest import wizard_payload

from openexits_panel.db import session as db_session
from openexits_panel.models import Submission, User
from openexits_panel.services.state_machine import transition


def test_dry_run_validate(contributor):
    client, headers = contributor
    r = client.post("/api/v1/validate", headers=headers, json=wizard_payload())
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["normalized"]["name"] == "Falaise Nouvelle"
    assert body["normalized"]["provenance"][0]["contributor"] == "test_user"


def test_nearby_endpoint(contributor):
    client, headers = contributor
    r = client.get("/api/v1/sites/nearby?lat=45.9013&lon=6.5124", headers=headers)
    hits = r.get_json()["hits"]
    assert len(hits) == 1
    assert hits[0]["name"] == "Pointe du Héron"
    assert hits[0]["distance_m"] < 30
    far = client.get("/api/v1/sites/nearby?lat=45.5&lon=6.0", headers=headers)
    assert far.get_json()["hits"] == []


def test_submission_reaches_pending_with_flags(contributor):
    client, headers = contributor
    r = client.post("/api/v1/submissions", headers=headers, json=wizard_payload())
    assert r.status_code == 201
    body = r.get_json()
    assert body["submission"]["status"] == "pending"
    assert body["machine_flags"]["no_landing"] is True
    assert body["machine_flags"]["duplicate_override"] is False

    with_lz = client.post("/api/v1/submissions", headers=headers,
                          json=wizard_payload(lat=45.75, name="Falaise Deux", with_landing=True))
    assert with_lz.get_json()["machine_flags"]["no_landing"] is False

    listing = client.get("/api/v1/submissions", headers=headers).get_json()["submissions"]
    assert len(listing) == 2


def test_new_site_within_gate_radius_rejected(contributor):
    client, headers = contributor
    r = client.post("/api/v1/submissions", headers=headers,
                    json=wizard_payload(lat=45.90125, lon=6.51232, name="Doublon"))
    assert r.status_code == 422
    body = r.get_json()
    assert body["error"] == "duplicate.too_close"
    assert body["hits"][0]["name"] == "Pointe du Héron"


def test_nearby_prompt_records_override_flag(contributor):
    client, headers = contributor
    # ~150 m away: allowed as a new site, but flagged for moderation
    r = client.post("/api/v1/submissions", headers=headers,
                    json=wizard_payload(lat=45.90255, lon=6.5123, name="Voisin Assumé",
                                        duplicateOverride=True))
    assert r.status_code == 201
    flags = r.get_json()["machine_flags"]
    assert flags["duplicate_override"] is True
    assert flags["nearby_hits"][0]["name"] == "Pointe du Héron"


def test_validation_failure_blocks_creation(contributor):
    client, headers = contributor
    bad = wizard_payload()
    bad["features"][0]["exitDirectionDeg"] = 720
    r = client.post("/api/v1/submissions", headers=headers, json=bad)
    assert r.status_code == 422
    assert r.get_json()["error"] == "validation_failed"
    assert any(f["rule_id"] == "OE-R10" for f in r.get_json()["report"])


def test_racing_contributors_see_each_other(commons_app, contributor):
    client, headers = contributor
    client.post("/api/v1/submissions", headers=headers,
                json=wizard_payload(lat=45.7123, lon=6.3123, name="Premier Arrivé"))
    r = client.get("/api/v1/sites/nearby?lat=45.71235&lon=6.31235", headers=headers)
    hits = r.get_json()["hits"]
    assert any(h["pending"] and h["name"] == "Premier Arrivé" for h in hits)


def test_correction_flow(contributor):
    client, headers = contributor
    payload = wizard_payload(kind="correction")
    payload["targetSitePath"] = "fr/pointe-du-heron"
    payload["site"] = {"access": "legal"}
    payload["features"] = []
    r = client.post("/api/v1/submissions", headers=headers, json=payload)
    assert r.status_code == 201
    detail = client.get(
        f"/api/v1/submissions/{r.get_json()['submission']['public_id']}", headers=headers
    ).get_json()["submission"]
    doc = detail["normalized"]
    assert doc["id"] == "01J9Y0AAAAAAAAAAAAAAAAAAAA"      # identity preserved
    assert doc["access"] == "legal"                        # overlay applied
    assert doc["provenance"][0]["contributor"] == "heron_n"  # history untouched
    assert len(doc["features"]) == 2                       # features kept


def test_withdraw_and_resubmit_cycle(commons_app, contributor):
    client, headers = contributor
    pid = client.post("/api/v1/submissions", headers=headers,
                      json=wizard_payload()).get_json()["submission"]["public_id"]

    # moderator requests changes (moderation API lands in Phase 6 — direct transition)
    with commons_app.app_context():
        db = db_session()
        try:
            sub = db.query(Submission).filter_by(public_id=pid).one()
            mod = User(handle="mod", email="m@example.invalid", password_hash="x",
                       role="moderator")
            db.add(mod)
            transition(db, sub, "changes_requested", as_role="moderator")
            db.commit()
        finally:
            db.close()

    r = client.post(f"/api/v1/submissions/{pid}/resubmit", headers=headers,
                    json=wizard_payload(with_landing=True))
    assert r.status_code == 200
    assert r.get_json()["submission"]["status"] == "pending"
    assert r.get_json()["machine_flags"]["no_landing"] is False

    w = client.post(f"/api/v1/submissions/{pid}/withdraw", headers=headers)
    assert w.status_code == 200
    assert w.get_json()["submission"]["status"] == "withdrawn"

    again = client.post(f"/api/v1/submissions/{pid}/withdraw", headers=headers)
    assert again.status_code == 409


def test_other_users_cannot_see_my_submission(commons_app, contributor):
    client, headers = contributor
    pid = client.post("/api/v1/submissions", headers=headers,
                      json=wizard_payload()).get_json()["submission"]["public_id"]
    from conftest import csrf_of, register
    other = commons_app.test_client()
    resp = register(other, handle="other_user", email="o@example.invalid")
    r = other.get(f"/api/v1/submissions/{pid}",
                  headers={"X-CSRF-Token": csrf_of(resp)})
    assert r.status_code == 404
