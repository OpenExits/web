"""/api/v1/auth/* and /api/v1/terms/accept.

Error payloads are machine keys + params, never sentences — the frontend
translates (i18n rule, ADR homepage/i18n).
"""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request, session as cookie_session
from sqlalchemy import select

from ..auth import (
    HANDLE_RE, current_user, hash_password, login_user, logout_user,
    require_auth, terms_current, verify_password,
)
from ..db import session as db_session
from ..models import TermsAcceptance, User

bp = Blueprint("auth", __name__, url_prefix="/api/v1")

MIN_PASSWORD_LEN = 10


def user_payload(db, user: User) -> dict:
    return {
        "id": user.id,
        "handle": user.handle,
        "role": user.role,
        "locale": user.locale,
        "terms_accepted": terms_current(db, user),
        "current_terms_version": current_app.config["TERMS_VERSION"],
    }


@bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    handle = (data.get("handle") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    locale = data.get("locale") if data.get("locale") in ("en", "fr") else "en"

    errors = {}
    if not HANDLE_RE.match(handle):
        errors["handle"] = "auth.handle_invalid"
    if "@" not in email or len(email) < 5:
        errors["email"] = "auth.email_invalid"
    if len(password) < MIN_PASSWORD_LEN:
        errors["password"] = "auth.password_too_short"
    if errors:
        return jsonify({"error": "validation", "fields": errors}), 422

    db = db_session()
    try:
        taken = db.execute(
            select(User).where((User.handle == handle) | (User.email == email))
        ).scalars().first()
        if taken:
            field = "handle" if taken.handle == handle else "email"
            return jsonify({"error": "validation", "fields": {field: "auth.already_taken"}}), 409
        user = User(handle=handle, email=email,
                    password_hash=hash_password(password), locale=locale)
        db.add(user)
        db.commit()
        login_user(user)
        return jsonify({"user": user_payload(db, user), "csrf": cookie_session["csrf"]}), 201
    finally:
        db.close()


@bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    db = db_session()
    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None or not user.is_active or not verify_password(user.password_hash, password):
            return jsonify({"error": "auth.bad_credentials"}), 401
        login_user(user)
        return jsonify({"user": user_payload(db, user), "csrf": cookie_session["csrf"]})
    finally:
        db.close()


@bp.post("/auth/logout")
@require_auth()
def logout():
    logout_user()
    return jsonify({"ok": True})


@bp.get("/auth/me")
def me():
    db = db_session()
    try:
        user = current_user(db)
        if user is None:
            return jsonify({"user": None})
        return jsonify({"user": user_payload(db, user), "csrf": cookie_session.get("csrf")})
    finally:
        db.close()


@bp.post("/terms/accept")
@require_auth()
def accept_terms():
    data = request.get_json(silent=True) or {}
    version = data.get("terms_version")
    if version != current_app.config["TERMS_VERSION"]:
        return jsonify({
            "error": "terms.version_mismatch",
            "required_version": current_app.config["TERMS_VERSION"],
        }), 422
    if not terms_current(g.db, g.user):
        g.db.add(TermsAcceptance(user_id=g.user.id, terms_version=version))
        g.db.commit()
    return jsonify({"ok": True, "terms_version": version}), 201
