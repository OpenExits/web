"""Phase 6 e2e: the full pipeline against a real local commons git repo —
approve -> branch -> gates -> merge -> build; failure path + retry;
bot-stamped provenance; append-only on corrections (verification items 8/10
panel-side)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import SYNTH_HERON, TestConfig, csrf_of, register, wizard_payload
from openexits_panel.app import create_app
from openexits_panel.db import session as db_session
from openexits_panel.models import User

REAL_COMMONS = Path(__file__).resolve().parents[3] / "commons"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, encoding="utf-8").stdout


@pytest.fixture()
def pub_commons(tmp_path):
    """A publishable commons: sites + the real ci/scripts toolchain + git."""
    from build_artifacts import build
    from openexits_validator.normalize import write_json

    repo = tmp_path / "commons"
    write_json(repo / "sites" / "fr" / "pointe-du-heron.json", SYNTH_HERON)
    for sub in ("ci", "scripts"):
        shutil.copytree(REAL_COMMONS / sub, repo / sub,
                        ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(REAL_COMMONS / ".gitignore", repo / ".gitignore")
    build(repo, repo / "build")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t",
                    "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "base"],
                   check=True)
    return repo


@pytest.fixture()
def pub_app(tmp_path, pub_commons):
    from openexits_panel.services import nearby
    nearby.invalidate()

    class Cfg(TestConfig):
        COMMONS_REPO_PATH = pub_commons
        MEDIA_ROOT = tmp_path / "media"

    return create_app(Cfg, create_tables=True)


@pytest.fixture()
def actors(pub_app):
    """contributor client+headers, moderator client+headers."""
    contributor = pub_app.test_client()
    resp = register(contributor)
    c_headers = {"X-CSRF-Token": csrf_of(resp)}
    contributor.post("/api/v1/terms/accept", headers=c_headers,
                     json={"terms_version": "contributor-terms-2026-08"})

    moderator = pub_app.test_client()
    resp = register(moderator, handle="mod_marie", email="mod@example.invalid")
    m_headers = {"X-CSRF-Token": csrf_of(resp)}
    with pub_app.app_context():
        db = db_session()
        try:
            db.query(User).filter_by(handle="mod_marie").one().role = "moderator"
            db.commit()
        finally:
            db.close()
    return contributor, c_headers, moderator, m_headers


def _submit(contributor, c_headers, **kw) -> str:
    r = contributor.post("/api/v1/submissions", headers=c_headers,
                         json=wizard_payload(**kw))
    assert r.status_code == 201, r.get_json()
    return r.get_json()["submission"]["public_id"]


def test_full_pipeline_new_site(pub_commons, actors):
    contributor, c_headers, moderator, m_headers = actors
    pid = _submit(contributor, c_headers, with_landing=True)

    q = moderator.get("/api/v1/moderation/queue", headers=m_headers).get_json()["queue"]
    assert q[0]["public_id"] == pid and q[0]["contributor"] == "test_user"

    r = moderator.post(f"/api/v1/moderation/submissions/{pid}/approve", headers=m_headers)
    assert r.status_code == 200, r.get_json()
    result = r.get_json()
    assert result["publish"]["ok"] is True
    assert result["submission"]["status"] == "published"
    site_path = result["publish"]["site"]
    assert site_path == "fr/falaise-nouvelle"

    # the file exists at HEAD with BOT-stamped provenance (standard names)
    site_file = pub_commons / "sites" / "fr" / "falaise-nouvelle.json"
    doc = json.loads(site_file.read_text(encoding="utf-8"))
    prov = doc["provenance"]
    assert len(prov) == 1
    assert prov[0]["source"] == "panel"
    assert prov[0]["sourceId"] == pid
    assert prov[0]["contributor"] == "test_user"
    assert prov[0]["reviewedBy"] == "mod_marie"
    assert prov[0]["licence"] == "ODbL-1.0"

    # merge commit recorded + trailers present + build regenerated
    sha = result["publish"]["sha"]
    log = _git(pub_commons, "log", "--format=%H %s", "-5")
    assert sha in log
    body = _git(pub_commons, "log", "--format=%B", "-1", f"{sha}^2")
    assert f"Submission: {pid}" in body and "Reviewed-by: mod_marie" in body
    sites_geojson = (pub_commons / "build" / "sites.geojson").read_text(encoding="utf-8")
    assert "Falaise Nouvelle" in sites_geojson
    assert _git(pub_commons, "status", "--porcelain").strip() == ""

    # ...and the new site is immediately visible to the nearby index
    near = contributor.get("/api/v1/sites/nearby?lat=45.7123&lon=6.3123",
                           headers=c_headers).get_json()["hits"]
    assert any(h["name"] == "Falaise Nouvelle" and not h["pending"] for h in near)


def test_correction_appends_provenance(pub_commons, actors):
    contributor, c_headers, moderator, m_headers = actors
    payload = wizard_payload(kind="correction")
    payload["targetSitePath"] = "fr/pointe-du-heron"
    payload["site"] = {"access": "legal"}
    payload["features"] = []
    r = contributor.post("/api/v1/submissions", headers=c_headers, json=payload)
    pid = r.get_json()["submission"]["public_id"]

    ok = moderator.post(f"/api/v1/moderation/submissions/{pid}/approve", headers=m_headers)
    assert ok.status_code == 200, ok.get_json()

    doc = json.loads((pub_commons / "sites" / "fr" / "pointe-du-heron.json")
                     .read_text(encoding="utf-8"))
    assert doc["access"] == "legal"
    assert len(doc["provenance"]) == 2
    assert doc["provenance"][0]["contributor"] == "heron_n"      # prior credit intact
    assert doc["provenance"][1]["contributor"] == "test_user"
    assert doc["provenance"][1]["reviewedBy"] == "mod_marie"


def test_gate_failure_then_retry(pub_commons, actors):
    """A gate class the panel cannot pre-evaluate (sensitive zone added after
    submission) fails at publish, leaves the repo clean, and retry succeeds
    once the zone is lifted."""
    from openexits_validator.normalize import write_json

    contributor, c_headers, moderator, m_headers = actors
    pid = _submit(contributor, c_headers)

    zones_file = pub_commons / "ci" / "sensitive-zones.json"
    write_json(zones_file, {"zones": [{"name": "zone fictive", "lat": 45.7123,
                                       "lon": 6.3123, "radiusM": 500}]})
    _git(pub_commons, "add", "ci")
    subprocess.run(["git", "-C", str(pub_commons), "-c", "user.name=t",
                    "-c", "user.email=t@example.invalid", "commit", "-q", "-m",
                    "add zone"], check=True)

    r = moderator.post(f"/api/v1/moderation/submissions/{pid}/approve", headers=m_headers)
    assert r.status_code == 422
    body = r.get_json()
    assert body["submission"]["status"] == "publish_failed"
    assert "OE-SENSITIVE" in body["publish"]["report"]
    # nothing half-landed: tree clean, no site file, no leftover branch
    assert not (pub_commons / "sites" / "fr" / "falaise-nouvelle.json").exists()
    assert _git(pub_commons, "status", "--porcelain").strip() == ""
    assert f"sub/{pid}" not in _git(pub_commons, "branch", "--list")

    write_json(zones_file, {"zones": []})
    _git(pub_commons, "add", "ci")
    subprocess.run(["git", "-C", str(pub_commons), "-c", "user.name=t",
                    "-c", "user.email=t@example.invalid", "commit", "-q", "-m",
                    "lift zone"], check=True)

    retry = moderator.post(f"/api/v1/moderation/submissions/{pid}/publish", headers=m_headers)
    assert retry.status_code == 200, retry.get_json()
    assert retry.get_json()["submission"]["status"] == "published"


def test_edit_then_approve(pub_commons, actors):
    contributor, c_headers, moderator, m_headers = actors
    pid = _submit(contributor, c_headers)

    edited = wizard_payload(with_landing=True)
    edited["site"]["name"] = "Falaise Corrigée Par Mod"
    r = moderator.put(f"/api/v1/moderation/submissions/{pid}/fields",
                      headers=m_headers, json=edited)
    assert r.status_code == 200
    ok = moderator.post(f"/api/v1/moderation/submissions/{pid}/approve", headers=m_headers)
    assert ok.status_code == 200
    assert ok.get_json()["publish"]["site"] == "fr/falaise-corrigee-par-mod"
    detail = moderator.get(f"/api/v1/moderation/submissions/{pid}",
                           headers=m_headers).get_json()["submission"]
    assert detail["payload"]["site"]["name"] == "Falaise Nouvelle"   # original preserved
    assert detail["moderator_payload"]["site"]["name"] == "Falaise Corrigée Par Mod"


def test_reject_and_request_changes_and_reports(pub_app, actors):
    contributor, c_headers, moderator, m_headers = actors
    pid = _submit(contributor, c_headers)
    rc = moderator.post(f"/api/v1/moderation/submissions/{pid}/request-changes",
                        headers=m_headers, json={"message": "Ajoutez l'atterrissage svp."})
    assert rc.get_json()["submission"]["status"] == "changes_requested"

    pid2 = _submit(contributor, c_headers, lat=45.75, name="Falaise Refusée")
    rj = moderator.post(f"/api/v1/moderation/submissions/{pid2}/reject",
                        headers=m_headers, json={"reason": "Doublon manifeste."})
    assert rj.get_json()["submission"]["status"] == "rejected"

    # reports lane: sensitive pinned first, triage closes it
    contributor.post("/api/v1/sites/01J9Y0AAAAAAAAAAAAAAAAAAAA/report",
                     headers=c_headers, json={"category": "other", "body": "x"})
    contributor.post("/api/v1/sites/01J9Y0AAAAAAAAAAAAAAAAAAAA/report",
                     headers=c_headers, json={"category": "sensitive", "body": "y"})
    lane = moderator.get("/api/v1/moderation/reports", headers=m_headers).get_json()["reports"]
    assert lane[0]["category"] == "sensitive"
    done = moderator.post(f"/api/v1/moderation/reports/{lane[0]['id']}/resolve",
                          headers=m_headers, json={"note": "scrub path checked"})
    assert done.get_json()["status"] == "resolved"

    # plain users cannot touch moderation
    denied = contributor.get("/api/v1/moderation/queue", headers=c_headers)
    assert denied.status_code == 403
