"""/api/v1/validate (dry-run) and /api/v1/sites/nearby — the wizard's live
helpers. Nothing here stores anything.
"""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from openexits_validator import validate_site

from ..auth import require_auth
from ..services import nearby
from ..services.normalizer import NormalizeError, normalize

bp = Blueprint("validate", __name__, url_prefix="/api/v1")


def report_payload(report) -> list[dict]:
    return [
        {"rule_id": f.rule_id, "level": f.level, "path": f.path, "message": f.message}
        for f in report.findings
    ]


@bp.post("/validate")
@require_auth()
def validate_dry_run():
    payload = request.get_json(silent=True) or {}
    try:
        doc = normalize(payload, contributor_handle=g.user.handle,
                        commons_repo=current_app.config["COMMONS_REPO_PATH"])
    except NormalizeError as exc:
        return jsonify({"error": exc.key}), 422
    report = validate_site(doc)
    return jsonify({"ok": report.ok, "report": report_payload(report), "normalized": doc})


@bp.get("/sites/nearby")
@require_auth()
def sites_nearby():
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
    except (KeyError, ValueError):
        return jsonify({"error": "nearby.bad_coordinates"}), 422
    radius = min(float(request.args.get("radius_m", nearby.PROMPT_RADIUS_M)), 2000.0)
    hits = nearby.sites_near(current_app.config["COMMONS_REPO_PATH"], g.db, lat, lon, radius)
    return jsonify({"hits": hits, "gate_radius_m": nearby.GATE_RADIUS_M})
