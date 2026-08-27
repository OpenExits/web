"""Public data routes: streaming, ETag/304, whitelist, traversal guard."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from conftest import TestConfig
from openexit_panel.app import create_app

COMMONS_SCRIPTS = Path(__file__).resolve().parents[3] / "commons" / "scripts"
sys.path.insert(0, str(COMMONS_SCRIPTS))

from build_artifacts import build  # noqa: E402
from openexit_validator.normalize import write_json  # noqa: E402

SYNTH_SITE = {
    "schemaVersion": "2.0",
    "id": "01J9W0AAAAAAAAAAAAAAAAAAAA",
    "name": "Falaise du Test Public",
    "country": "FR",
    "status": "open",
    "access": "unknown",
    "sensitivity": "public",
    "provenance": [{"source": "panel", "contributor": "t", "contributedAt": "2026-08-27",
                    "licence": "ODbL-1.0"}],
    "updatedAt": "2026-08-27T09:00:00Z",
    "features": [{
        "role": "exit",
        "position": {"lat": 45.712345, "lon": 6.312345, "elevationM": 1500},
        "suitability": {"sliderOff": True},
        "exitDirectionDeg": 90,
    }],
}


@pytest.fixture()
def commons_client(tmp_path):
    repo = tmp_path / "commons"
    write_json(repo / "sites" / "fr" / "falaise-du-test-public.json", SYNTH_SITE)
    build(repo, repo / "build")

    class Cfg(TestConfig):
        COMMONS_REPO_PATH = repo

    app = create_app(Cfg, create_tables=True)
    return app.test_client()


def test_geojson_served_with_etag_and_304(commons_client):
    r = commons_client.get("/api/v1/public/data/sites.geojson")
    assert r.status_code == 200
    assert r.mimetype == "application/geo+json"
    body = r.get_json(force=True)
    assert body["features"][0]["properties"]["name"] == "Falaise du Test Public"
    assert body["features"][0]["geometry"]["coordinates"][0] == pytest.approx(6.312345)
    etag = r.headers["ETag"]
    r304 = commons_client.get("/api/v1/public/data/sites.geojson",
                              headers={"If-None-Match": etag})
    assert r304.status_code == 304


def test_build_whitelist(commons_client):
    assert commons_client.get("/api/v1/public/data/secrets.txt").status_code == 404
    assert commons_client.get("/api/v1/public/data/../sites/fr/x.json").status_code == 404


def test_site_document_and_traversal_guard(commons_client):
    r = commons_client.get("/api/v1/public/sites/fr/falaise-du-test-public")
    assert r.status_code == 200
    assert r.get_json(force=True)["name"] == "Falaise du Test Public"
    assert commons_client.get("/api/v1/public/sites/fr/none-such").status_code == 404
    assert commons_client.get("/api/v1/public/sites/FR/Falaise").status_code == 404
    assert commons_client.get("/api/v1/public/sites/fr/..%2f..%2fci%2fgates-config").status_code == 404


def test_missing_build_reports_no_data(tmp_path):
    class Cfg(TestConfig):
        COMMONS_REPO_PATH = tmp_path / "empty-commons"

    app = create_app(Cfg, create_tables=True)
    r = app.test_client().get("/api/v1/public/data/sites.geojson")
    assert r.status_code == 404
    assert r.get_json()["error"] == "no_data_yet"
