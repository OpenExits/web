"""/api/v1/submissions — the contributor pipeline entrance.

Server-side truth: instant validation and the nearby check are re-run here
regardless of what the client showed (client results are UX only).
"""
from __future__ import annotations

import json

from flask import Blueprint, current_app, g, jsonify, request, send_file
from sqlalchemy import select
from ulid import ULID

from openexits_validator import validate_site

from ..auth import require_auth, require_current_terms
from ..db import session as db_session
from ..models import (
    MediaUpload, Submission, SubmissionEvent, SubmissionMessage, TermsAcceptance, utcnow,
)
from ..services import nearby
from ..services.media_store import MediaError, process_and_store
from ..services.normalizer import NormalizeError, normalize
from ..services.state_machine import InvalidTransition, transition
from .validate_routes import report_payload

bp = Blueprint("submissions", __name__, url_prefix="/api/v1")


def _summary(sub: Submission) -> dict:
    doc = json.loads(sub.normalized_json) if sub.normalized_json else {}
    return {
        "public_id": sub.public_id,
        "kind": sub.kind,
        "status": sub.status,
        "site_name": doc.get("name"),
        "target_site_id": sub.target_site_id,
        "created_at": sub.created_at,
        "updated_at": sub.updated_at,
        "published_site_id": sub.published_site_id,
    }


def _detail(db, sub: Submission, *, include_moderator_only: bool) -> dict:
    msgs = db.execute(
        select(SubmissionMessage).where(SubmissionMessage.submission_id == sub.id)
        .order_by(SubmissionMessage.created_at)
    ).scalars().all()
    media = db.execute(
        select(MediaUpload).where(MediaUpload.submission_id == sub.id)
    ).scalars().all()
    return {
        **_summary(sub),
        "payload": json.loads(sub.payload_json),
        "normalized": json.loads(sub.normalized_json) if sub.normalized_json else None,
        "machine_flags": json.loads(sub.machine_flags_json),
        "messages": [
            {"id": m.id, "author_user_id": m.author_user_id, "body": m.body,
             "visibility": m.visibility, "created_at": m.created_at}
            for m in msgs
            if include_moderator_only or m.visibility == "public"
        ],
        "media": [{"sha256": m.sha256, "width": m.width, "height": m.height,
                   "caption": m.caption, "mime_type": m.mime_type} for m in media],
    }


def _current_terms_acceptance(db, user_id: int) -> TermsAcceptance:
    return db.execute(
        select(TermsAcceptance)
        .where(TermsAcceptance.user_id == user_id,
               TermsAcceptance.terms_version == current_app.config["TERMS_VERSION"])
        .order_by(TermsAcceptance.id.desc()).limit(1)
    ).scalar_one()


def _machine_flags(payload: dict, doc: dict, report, hits: list[dict]) -> dict:
    features = doc.get("features", [])
    return {
        "validator": report_payload(report),
        "nearby_hits": hits,
        "duplicate_override": bool(payload.get("duplicateOverride")),
        "no_landing": payload.get("kind") == "new_site"
                      and not any(f.get("role") == "landing" for f in features),
    }


def _validate_and_flag(payload: dict):
    """Normalize + validate + nearby. Returns (doc, flags) or an error resp."""
    commons = current_app.config["COMMONS_REPO_PATH"]
    try:
        doc = normalize(payload, contributor_handle=g.user.handle, commons_repo=commons)
    except NormalizeError as exc:
        return None, (jsonify({"error": exc.key}), 422)
    report = validate_site(doc)
    if not report.ok:
        return None, (jsonify({"error": "validation_failed",
                               "report": report_payload(report)}), 422)
    hits: list[dict] = []
    if payload.get("kind") == "new_site":
        exit_feat = next((f for f in doc["features"] if f.get("role") == "exit"),
                         doc["features"][0])
        pos = exit_feat["position"]
        hits = nearby.sites_near(commons, g.db, pos["lat"], pos["lon"])
        too_close = [h for h in hits if h["distance_m"] < nearby.GATE_RADIUS_M]
        if too_close:
            return None, (jsonify({"error": "duplicate.too_close",
                                   "hits": too_close,
                                   "gate_radius_m": nearby.GATE_RADIUS_M}), 422)
    return (doc, _machine_flags(payload, doc, report, hits)), None


@bp.post("/submissions")
@require_auth()
@require_current_terms
def create_submission():
    payload = request.get_json(silent=True) or {}
    result, err = _validate_and_flag(payload)
    if err:
        return err
    doc, flags = result
    sub = Submission(
        public_id=str(ULID()),
        user_id=g.user.id,
        kind=payload["kind"],
        target_site_id=payload.get("targetSitePath"),
        payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
        normalized_json=json.dumps(doc, ensure_ascii=False, sort_keys=True),
        machine_flags_json=json.dumps(flags, ensure_ascii=False, sort_keys=True),
        terms_acceptance_id=_current_terms_acceptance(g.db, g.user.id).id,
    )
    g.db.add(sub)
    g.db.flush()
    g.db.add(SubmissionEvent(submission_id=sub.id, actor_user_id=g.user.id,
                             event="created", to_status="pending"))
    g.db.commit()
    return jsonify({"submission": _summary(sub), "machine_flags": flags}), 201


@bp.get("/submissions")
@require_auth()
def list_own():
    subs = g.db.execute(
        select(Submission).where(Submission.user_id == g.user.id)
        .order_by(Submission.created_at.desc())
    ).scalars().all()
    return jsonify({"submissions": [_summary(s) for s in subs]})


def _load_for(db, public_id: str, *, owner_or_moderator: bool = True) -> Submission | None:
    sub = db.execute(
        select(Submission).where(Submission.public_id == public_id)
    ).scalar_one_or_none()
    if sub is None:
        return None
    is_owner = sub.user_id == g.user.id
    is_mod = g.user.role in ("moderator", "admin")
    if owner_or_moderator and not (is_owner or is_mod):
        return None
    return sub


@bp.get("/submissions/<public_id>")
@require_auth()
def detail(public_id: str):
    sub = _load_for(g.db, public_id)
    if sub is None:
        return jsonify({"error": "not_found"}), 404
    is_mod = g.user.role in ("moderator", "admin")
    return jsonify({"submission": _detail(g.db, sub, include_moderator_only=is_mod)})


@bp.post("/submissions/<public_id>/resubmit")
@require_auth()
@require_current_terms
def resubmit(public_id: str):
    sub = _load_for(g.db, public_id)
    if sub is None or sub.user_id != g.user.id:
        return jsonify({"error": "not_found"}), 404
    payload = request.get_json(silent=True) or {}
    result, err = _validate_and_flag(payload)
    if err:
        return err
    doc, flags = result
    try:
        transition(g.db, sub, "pending", as_role="owner", actor_user_id=g.user.id)
    except InvalidTransition:
        return jsonify({"error": "submission.bad_state", "status": sub.status}), 409
    sub.payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    sub.normalized_json = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    sub.machine_flags_json = json.dumps(flags, ensure_ascii=False, sort_keys=True)
    sub.updated_at = utcnow()
    g.db.commit()
    return jsonify({"submission": _summary(sub), "machine_flags": flags})


@bp.post("/submissions/<public_id>/withdraw")
@require_auth()
def withdraw(public_id: str):
    sub = _load_for(g.db, public_id)
    if sub is None or sub.user_id != g.user.id:
        return jsonify({"error": "not_found"}), 404
    try:
        transition(g.db, sub, "withdrawn", as_role="owner", actor_user_id=g.user.id)
    except InvalidTransition:
        return jsonify({"error": "submission.bad_state", "status": sub.status}), 409
    g.db.commit()
    return jsonify({"submission": _summary(sub)})


@bp.post("/submissions/<public_id>/messages")
@require_auth()
def post_message(public_id: str):
    sub = _load_for(g.db, public_id)
    if sub is None:
        return jsonify({"error": "not_found"}), 404
    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "message.empty"}), 422
    is_mod = g.user.role in ("moderator", "admin")
    visibility = "moderator_only" if (is_mod and data.get("visibility") == "moderator_only") else "public"
    g.db.add(SubmissionMessage(submission_id=sub.id, author_user_id=g.user.id,
                               body=body, visibility=visibility))
    g.db.add(SubmissionEvent(submission_id=sub.id, actor_user_id=g.user.id, event="message"))
    g.db.commit()
    return jsonify({"ok": True}), 201


@bp.post("/submissions/<public_id>/media")
@require_auth()
def upload_media(public_id: str):
    sub = _load_for(g.db, public_id)
    if sub is None or sub.user_id != g.user.id:
        return jsonify({"error": "not_found"}), 404
    if sub.status != "pending":
        return jsonify({"error": "submission.bad_state", "status": sub.status}), 409
    file = request.files.get("file")
    if file is None:
        return jsonify({"error": "media.file_missing"}), 422
    try:
        processed = process_and_store(file.read(), current_app.config["MEDIA_ROOT"])
    except MediaError as exc:
        return jsonify({"error": exc.key}), 422
    existing = g.db.execute(
        select(MediaUpload).where(MediaUpload.sha256 == processed.sha256)
    ).scalar_one_or_none()
    if existing is None:
        g.db.add(MediaUpload(
            sha256=processed.sha256, submission_id=sub.id, uploader_user_id=g.user.id,
            original_filename=file.filename, mime_type=processed.mime_type,
            size_bytes=processed.size_bytes, width=processed.width,
            height=processed.height, caption=request.form.get("caption"),
            storage_path=processed.storage_path,
        ))
        g.db.commit()
    return jsonify({"sha256": processed.sha256, "width": processed.width,
                    "height": processed.height}), 201


@bp.get("/media/<sha256>")
def serve_media(sha256: str):
    db = db_session()
    try:
        media = db.execute(
            select(MediaUpload).where(MediaUpload.sha256 == sha256)
        ).scalar_one_or_none()
        if media is None:
            return jsonify({"error": "not_found"}), 404
        if not media.published:
            from ..auth import current_user
            user = current_user(db)
            allowed = user is not None and (
                user.role in ("moderator", "admin") or user.id == media.uploader_user_id
            )
            if not allowed:
                return jsonify({"error": "not_found"}), 404
        path = current_app.config["MEDIA_ROOT"] / media.storage_path
        if not path.exists():
            return jsonify({"error": "not_found"}), 404
        return send_file(path, mimetype=media.mime_type)
    finally:
        db.close()
