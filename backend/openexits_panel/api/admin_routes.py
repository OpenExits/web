"""/api/v1/admin/* — user roles and data releases."""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import select

from ..auth import require_auth
from ..models import ROLES, User
from ..services.publisher import PublishError, tag_release

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


@bp.get("/users")
@require_auth(role="admin")
def users():
    rows = g.db.execute(select(User).order_by(User.created_at)).scalars().all()
    return jsonify({"users": [
        {"id": u.id, "handle": u.handle, "role": u.role, "is_active": u.is_active,
         "created_at": u.created_at}
        for u in rows
    ]})


@bp.put("/users/<int:user_id>/role")
@require_auth(role="admin")
def set_role(user_id: int):
    role = (request.get_json(silent=True) or {}).get("role")
    if role not in ROLES:
        return jsonify({"error": "admin.bad_role", "roles": list(ROLES)}), 422
    user = g.db.get(User, user_id)
    if user is None:
        return jsonify({"error": "not_found"}), 404
    user.role = role
    g.db.commit()
    return jsonify({"ok": True, "handle": user.handle, "role": role})


@bp.post("/release")
@require_auth(role="admin")
def release():
    tag = (request.get_json(silent=True) or {}).get("tag")
    if not tag:
        return jsonify({"error": "admin.tag_required"}), 422
    try:
        tag_release(current_app.config["COMMONS_REPO_PATH"], tag)
    except PublishError as exc:
        return jsonify({"error": exc.key, "detail": exc.detail}), 422
    return jsonify({"ok": True, "tag": tag}), 201
