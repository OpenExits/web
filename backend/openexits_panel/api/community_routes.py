"""ADR-7 community layer: threads, confirmed-current, report-a-problem.

Panel-DB only — never touches the commons. The public read endpoint is
separate from the data routes so those stay CDN-swappable.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import func, select

from ..auth import require_auth
from ..db import session as db_session
from ..models import REPORT_CATEGORIES, SiteComment, SiteConfirmation, SiteReport, User, utcnow
from ..services import nearby
from .public_routes import SEGMENT_RE

bp = Blueprint("community", __name__, url_prefix="/api/v1")

ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
MAX_COMMENT_LEN = 4000


def _confirmation_summary(db, site_id: str) -> dict:
    last = db.execute(
        select(func.max(SiteConfirmation.confirmed_on))
        .where(SiteConfirmation.site_id == site_id)
    ).scalar_one_or_none()
    window_start = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    count_12mo = db.execute(
        select(func.count()).select_from(SiteConfirmation)
        .where(SiteConfirmation.site_id == site_id,
               SiteConfirmation.confirmed_on >= window_start)
    ).scalar_one()
    return {"last_confirmed_on": last, "confirmations_12mo": count_12mo}


@bp.get("/public/sites/<country>/<slug>/community")
def community(country: str, slug: str):
    if not (SEGMENT_RE.match(country) and SEGMENT_RE.match(slug)):
        return jsonify({"error": "not_found"}), 404
    site_path = current_app.config["COMMONS_REPO_PATH"] / "sites" / country / f"{slug}.json"
    if not site_path.exists():
        return jsonify({"error": "not_found"}), 404
    from openexits_validator.normalize import read_json
    site_id = read_json(site_path).get("id")
    db = db_session()
    try:
        rows = db.execute(
            select(SiteComment, User.handle)
            .join(User, User.id == SiteComment.user_id)
            .where(SiteComment.site_id == site_id, SiteComment.deleted_at.is_(None))
            .order_by(SiteComment.created_at)
        ).all()
        return jsonify({
            "site_id": site_id,
            "comments": [
                {"id": c.id, "handle": handle, "body": c.body, "created_at": c.created_at}
                for c, handle in rows
            ],
            "confirmations": _confirmation_summary(db, site_id),
        })
    finally:
        db.close()


def _known_site_or_none(site_id: str):
    if not ULID_RE.match(site_id):
        return jsonify({"error": "not_found"}), 404
    if not nearby.site_exists(current_app.config["COMMONS_REPO_PATH"], site_id):
        return jsonify({"error": "site.unknown"}), 404
    return None


@bp.post("/sites/<site_id>/comments")
@require_auth()
def post_comment(site_id: str):
    err = _known_site_or_none(site_id)
    if err:
        return err
    body = ((request.get_json(silent=True) or {}).get("body") or "").strip()
    if not body:
        return jsonify({"error": "comment.empty"}), 422
    if len(body) > MAX_COMMENT_LEN:
        return jsonify({"error": "comment.too_long"}), 422
    comment = SiteComment(site_id=site_id, user_id=g.user.id, body=body)
    g.db.add(comment)
    g.db.commit()
    return jsonify({"id": comment.id, "created_at": comment.created_at}), 201


@bp.delete("/comments/<int:comment_id>")
@require_auth()
def delete_comment(comment_id: int):
    comment = g.db.get(SiteComment, comment_id)
    if comment is None or comment.deleted_at is not None:
        return jsonify({"error": "not_found"}), 404
    is_mod = g.user.role in ("moderator", "admin")
    if not (is_mod or comment.user_id == g.user.id):
        return jsonify({"error": "forbidden"}), 403
    comment.deleted_at = utcnow()
    comment.deleted_by = g.user.id
    g.db.commit()
    return jsonify({"ok": True})


@bp.post("/sites/<site_id>/confirm")
@require_auth()
def confirm_site(site_id: str):
    err = _known_site_or_none(site_id)
    if err:
        return err
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = g.db.execute(
        select(SiteConfirmation).where(SiteConfirmation.site_id == site_id,
                                       SiteConfirmation.user_id == g.user.id)
    ).scalar_one_or_none()
    if existing is None:
        g.db.add(SiteConfirmation(site_id=site_id, user_id=g.user.id, confirmed_on=today))
    else:
        existing.confirmed_on = today  # re-confirm refreshes, never duplicates
    g.db.commit()
    return jsonify({"confirmed_on": today, **_confirmation_summary(g.db, site_id)}), 201


@bp.post("/sites/<site_id>/report")
@require_auth()
def report_site(site_id: str):
    err = _known_site_or_none(site_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    category = data.get("category")
    if category not in REPORT_CATEGORIES:
        return jsonify({"error": "report.category_required",
                        "categories": list(REPORT_CATEGORIES)}), 422
    report = SiteReport(site_id=site_id, user_id=g.user.id, category=category,
                        body=(data.get("body") or "").strip() or None)
    g.db.add(report)
    g.db.commit()
    return jsonify({"id": report.id, "status": report.status}), 201
