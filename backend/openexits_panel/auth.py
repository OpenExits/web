"""Session auth: argon2id hashing, cookie sessions, role guards, CSRF,
current-terms enforcement. Deliberately dependency-light (no flask-login):
the session holds user_id + a CSRF token, nothing else.
"""
from __future__ import annotations

import re
import secrets
from functools import wraps

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import current_app, g, jsonify, request, session as cookie_session
from sqlalchemy import select

from .db import session as db_session
from .models import TermsAcceptance, User

_hasher = PasswordHasher()  # argon2id defaults

HANDLE_RE = re.compile(r"^[a-z0-9_][a-z0-9_-]{2,31}$")

CSRF_EXEMPT_ENDPOINTS = {"auth.register", "auth.login"}


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def login_user(user: User) -> None:
    cookie_session.clear()
    cookie_session["user_id"] = user.id
    cookie_session["csrf"] = secrets.token_urlsafe(32)


def logout_user() -> None:
    cookie_session.clear()


def current_user(db) -> User | None:
    uid = cookie_session.get("user_id")
    if uid is None:
        return None
    user = db.get(User, uid)
    if user is None or not user.is_active:
        return None
    return user


def csrf_ok() -> bool:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    if request.endpoint in CSRF_EXEMPT_ENDPOINTS:
        return True
    return request.headers.get("X-CSRF-Token") == cookie_session.get("csrf")


def require_auth(role: str = "user"):
    """Decorator: authenticated (+ CSRF on mutations) with at least `role`.
    Puts the user on g.user and an open db session on g.db."""
    order = {"user": 0, "moderator": 1, "admin": 2}

    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            db = db_session()
            try:
                user = current_user(db)
                if user is None:
                    return jsonify({"error": "auth_required"}), 401
                if not csrf_ok():
                    return jsonify({"error": "csrf"}), 403
                if order[user.role] < order[role]:
                    return jsonify({"error": "forbidden"}), 403
                g.db, g.user = db, user
                return fn(*args, **kwargs)
            finally:
                db.close()
        return wrapper
    return deco


def terms_current(db, user: User) -> bool:
    version = current_app.config["TERMS_VERSION"]
    row = db.execute(
        select(TermsAcceptance)
        .where(TermsAcceptance.user_id == user.id,
               TermsAcceptance.terms_version == version)
        .limit(1)
    ).scalar_one_or_none()
    return row is not None


def require_current_terms(fn):
    """Stack under @require_auth on any endpoint that creates contributions:
    a terms-version bump blocks until the user re-accepts."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not terms_current(g.db, g.user):
            return jsonify({
                "error": "terms_outdated",
                "required_version": current_app.config["TERMS_VERSION"],
            }), 428
        return fn(*args, **kwargs)
    return wrapper
