from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from openexits_panel.app import create_app
from openexits_panel.config import Config

# The panel's job is to publish into a commons clone, so the tests that exercise
# publishing need commons/scripts on the path. That is a sibling checkout, which a
# contributor cloning only this repository will not have.
#
# Resolve it if present, and let the tests that need it skip cleanly if not, rather
# than failing collection for the whole suite -- a contributor running pytest on a
# bare `web` clone should get a passing run, not an ImportError. CI checks commons
# out alongside so nothing is silently skipped there.
#
# Override with OPENEXITS_COMMONS_PATH when the checkout lives somewhere else.
_env_commons = os.environ.get("OPENEXITS_COMMONS_PATH")
COMMONS_REPO = (
    Path(_env_commons).resolve() if _env_commons
    else Path(__file__).resolve().parents[3] / "commons"
)
COMMONS_SCRIPTS = COMMONS_REPO / "scripts"
HAVE_COMMONS = (COMMONS_SCRIPTS / "build_artifacts.py").is_file()

if HAVE_COMMONS and str(COMMONS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(COMMONS_SCRIPTS))

requires_commons = pytest.mark.skipif(
    not HAVE_COMMONS,
    reason=(
        f"needs a commons checkout at {COMMONS_REPO} (or OPENEXITS_COMMONS_PATH); "
        "clone OpenExits/commons beside this repository to run these"
    ),
)


class TestConfig(Config):
    TESTING = True
    DB_URL = "sqlite://"          # in-memory, per test app
    SECRET_KEY = "test-secret"
    TERMS_VERSION = "contributor-terms-2026-08"


@pytest.fixture()
def app():
    app = create_app(TestConfig, create_tables=True)
    # test-only probe endpoints (must be registered before the first request)
    from openexits_panel.auth import require_auth, require_current_terms

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


SYNTH_HERON = {
    "schemaVersion": "2.0",
    "id": "01J9Y0AAAAAAAAAAAAAAAAAAAA",
    "name": "Pointe du Héron",
    "country": "FR",
    "status": "open",
    "access": "tolerated",
    "sensitivity": "public",
    "provenance": [{"source": "panel", "contributor": "heron_n",
                    "contributedAt": "2026-04-02", "licence": "ODbL-1.0"}],
    "updatedAt": "2026-08-27T09:00:00Z",
    "features": [
        {"role": "exit", "name": "High exit",
         "position": {"lat": 45.9012, "lon": 6.5123, "elevationM": 2140},
         "objectType": "earth", "suitability": {"sliderOff": True, "wingsuit": True},
         "exitDirectionDeg": 210},
        {"role": "landing", "name": "Pré Rond", "surface": "grass",
         "position": {"lat": 45.8951, "lon": 6.5089, "elevationM": 1180}},
    ],
}


@pytest.fixture()
def commons_repo(tmp_path):
    """A tmp commons with one published synthetic site + built artifacts.

    Skipping here rather than at each test site means everything downstream --
    commons_app, contributor, and every test built on them -- skips with it.
    """
    if not HAVE_COMMONS:
        pytest.skip(requires_commons.kwargs["reason"])

    from build_artifacts import build
    from openexits_validator.normalize import write_json

    repo = tmp_path / "commons"
    write_json(repo / "sites" / "fr" / "pointe-du-heron.json", SYNTH_HERON)
    build(repo, repo / "build")
    return repo


@pytest.fixture()
def commons_app(tmp_path, commons_repo):
    from openexits_panel.services import nearby
    nearby.invalidate()

    class Cfg(TestConfig):
        COMMONS_REPO_PATH = commons_repo
        MEDIA_ROOT = tmp_path / "media"

    return create_app(Cfg, create_tables=True)


@pytest.fixture()
def contributor(commons_app):
    """(client, headers) for a registered user with current terms accepted."""
    client = commons_app.test_client()
    resp = register(client)
    headers = {"X-CSRF-Token": csrf_of(resp)}
    client.post("/api/v1/terms/accept", headers=headers,
                json={"terms_version": "contributor-terms-2026-08"})
    return client, headers


def wizard_payload(*, lat=45.7123, lon=6.3123, name="Falaise Nouvelle",
                   with_landing=False, kind="new_site", **extra):
    features = [{
        "role": "exit", "lat": lat, "lon": lon, "elevationM": 1500,
        "positionSource": "gps", "precisionM": 10, "objectType": "earth",
        "suitability": {"sliderOff": True, "tracksuit": True},
        "exitDirectionDeg": 180,
        "measurements": {"rockdrop": {"valueM": 150, "method": "estimate",
                                      "measuredAt": "2026-08"}},
    }]
    if with_landing:
        features.append({"role": "landing", "lat": lat - 0.004, "lon": lon + 0.002,
                         "elevationM": 900, "positionSource": "map", "surface": "grass"})
    payload = {
        "kind": kind,
        "site": {"name": name, "country": "FR", "status": "open", "access": "tolerated"},
        "features": features,
        "notes": {"language": "fr", "observations": "Site fictif de test."},
    }
    payload.update(extra)
    return payload
