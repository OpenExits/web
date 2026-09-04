"""/api/v1/public/* — deliberately dumb readers of the commons working tree.

These routes stream files; they hold no state and no logic beyond ETags, so
they can later be replaced by a CDN serving tagged releases without touching
the map client (ADR-1 graduation path).
"""
from __future__ import annotations

import re
from pathlib import Path

from flask import Blueprint, Response, current_app, jsonify, request, send_file

bp = Blueprint("public", __name__, url_prefix="/api/v1/public")

BUILD_FILES = {
    "sites.geojson": "application/geo+json",
    "features.geojson": "application/geo+json",
    "routes.geojson": "application/geo+json",
    "sites.csv": "text/csv",
    "media-index.json": "application/json",
}

SEGMENT_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")  # country + slug; no dots, no slashes


def _commons() -> Path:
    return Path(current_app.config["COMMONS_REPO_PATH"])


def _etag_of(path: Path) -> str:
    stat = path.stat()
    return f'"{stat.st_mtime_ns:x}-{stat.st_size:x}"'


def _with_etag(path: Path, mimetype: str) -> Response:
    etag = _etag_of(path)
    if request.headers.get("If-None-Match") == etag:
        resp = Response(status=304)
    else:
        resp = send_file(path, mimetype=mimetype, conditional=False)
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = "public, max-age=60"
    return resp


@bp.get("/data/<name>")
def build_artifact(name: str):
    mimetype = BUILD_FILES.get(name)
    if mimetype is None:
        return jsonify({"error": "not_found"}), 404
    path = _commons() / "build" / name
    if not path.exists():
        return jsonify({"error": "no_data_yet"}), 404
    return _with_etag(path, mimetype)


@bp.get("/sites/<country>/<slug>")
def site_document(country: str, slug: str):
    if not (SEGMENT_RE.match(country) and SEGMENT_RE.match(slug)):
        return jsonify({"error": "not_found"}), 404
    path = _commons() / "sites" / country / f"{slug}.json"
    if not path.exists():
        return jsonify({"error": "not_found"}), 404
    return _with_etag(path, "application/json")
