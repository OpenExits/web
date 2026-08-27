"""/api/v1/moderation/* — review-before-publish (moderator+).

Two lanes: submissions (the pipeline) and reports (ADR-7 tickets, `sensitive`
pinned first). Edit-then-approve edits the WIZARD payload and re-runs the one
normalizer; a guarded raw-normalized escape hatch exists for schema corners.
"""
from __future__ import annotations

import json

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import select

from openexit_validator import validate_site

from ..auth import require_auth
from ..models import (
    SiteReport, Submission, SubmissionEvent, SubmissionMessage, User, utcnow,
)
from ..services.normalizer import NormalizeError, normalize
from ..services.publisher import PublishBusy, publish
from ..services.state_machine import EDITABLE_STATES, InvalidTransition, transition
from .submission_routes import _detail, _summary
from .validate_routes import report_payload

bp = Blueprint("moderation", __name__, url_prefix="/api/v1/moderation")


def _load(public_id: str) -> Submission | None:
    return g.db.execute(
        select(Submission).where(Submission.public_id == public_id)
    ).scalar_one_or_none()


@bp.get("/queue")
@require_auth(role="moderator")
def queue():
    status = request.args.get("status", "pending")
    rows = g.db.execute(
        select(Submission, User.handle)
        .join(User, User.id == Submission.user_id)
        .where(Submission.status == status)
        .order_by(Submission.created_at)
    ).all()
    out = []
    for sub, handle in rows:
        flags = json.loads(sub.machine_flags_json)
        published_count = g.db.execute(
            select(Submission).where(Submission.user_id == sub.user_id,
                                     Submission.status == "published")
        ).scalars().all()
        out.append({
            **_summary(sub),
            "contributor": handle,
            "contributor_published": len(published_count),
            "flags": {
                "duplicate_override": flags.get("duplicate_override", False),
                "no_landing": flags.get("no_landing", False),
                "validator_warns": sum(1 for f in flags.get("validator", [])
                                       if f.get("level") == "WARN"),
            },
        })
    return jsonify({"queue": out})


@bp.get("/submissions/<public_id>")
@require_auth(role="moderator")
def detail(public_id: str):
    sub = _load(public_id)
    if sub is None:
        return jsonify({"error": "not_found"}), 404
    contributor = g.db.get(User, sub.user_id)
    payload = _detail(g.db, sub, include_moderator_only=True)
    payload["contributor"] = contributor.handle
    payload["moderator_payload"] = (
        json.loads(sub.moderator_payload_json) if sub.moderator_payload_json else None
    )
    return jsonify({"submission": payload})


@bp.put("/submissions/<public_id>/fields")
@require_auth(role="moderator")
def edit_fields(public_id: str):
    """Edit-then-approve: a full wizard payload, re-normalized + re-validated.
    The contributor's original payload_json is never mutated (evidence)."""
    sub = _load(public_id)
    if sub is None:
        return jsonify({"error": "not_found"}), 404
    if sub.status not in EDITABLE_STATES:
        return jsonify({"error": "submission.bad_state", "status": sub.status}), 409
    payload = request.get_json(silent=True) or {}
    try:
        doc = normalize(payload, contributor_handle=g.db.get(User, sub.user_id).handle,
                        commons_repo=current_app.config["COMMONS_REPO_PATH"])
    except NormalizeError as exc:
        return jsonify({"error": exc.key}), 422
    report = validate_site(doc)
    if not report.ok:
        return jsonify({"error": "validation_failed", "report": report_payload(report)}), 422
    before = sub.moderator_payload_json or sub.payload_json
    sub.moderator_payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    sub.normalized_json = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    sub.updated_at = utcnow()
    g.db.add(SubmissionEvent(
        submission_id=sub.id, actor_user_id=g.user.id, event="moderator_edit",
        detail_json=json.dumps({"before": json.loads(before), "after": payload},
                               ensure_ascii=False, sort_keys=True),
    ))
    g.db.commit()
    return jsonify({"ok": True, "report": report_payload(report), "normalized": doc})


@bp.put("/submissions/<public_id>/normalized")
@require_auth(role="moderator")
def edit_normalized(public_id: str):
    """Escape hatch: raw normalized JSON. Still validated — a moderator cannot
    hand-produce a document the validator rejects."""
    sub = _load(public_id)
    if sub is None:
        return jsonify({"error": "not_found"}), 404
    if sub.status not in EDITABLE_STATES:
        return jsonify({"error": "submission.bad_state", "status": sub.status}), 409
    doc = request.get_json(silent=True)
    if not isinstance(doc, dict):
        return jsonify({"error": "moderation.not_a_document"}), 422
    report = validate_site(doc)
    if not report.ok:
        return jsonify({"error": "validation_failed", "report": report_payload(report)}), 422
    sub.normalized_json = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    sub.updated_at = utcnow()
    g.db.add(SubmissionEvent(submission_id=sub.id, actor_user_id=g.user.id,
                             event="moderator_edit",
                             detail_json=json.dumps({"raw_normalized": True})))
    g.db.commit()
    return jsonify({"ok": True, "report": report_payload(report)})


def _message(sub: Submission, body: str, visibility: str = "public") -> None:
    g.db.add(SubmissionMessage(submission_id=sub.id, author_user_id=g.user.id,
                               body=body, visibility=visibility))


@bp.post("/submissions/<public_id>/request-changes")
@require_auth(role="moderator")
def request_changes(public_id: str):
    sub = _load(public_id)
    if sub is None:
        return jsonify({"error": "not_found"}), 404
    body = ((request.get_json(silent=True) or {}).get("message") or "").strip()
    if not body:
        return jsonify({"error": "message.empty"}), 422
    try:
        transition(g.db, sub, "changes_requested", as_role=g.user.role,
                   actor_user_id=g.user.id)
    except InvalidTransition:
        return jsonify({"error": "submission.bad_state", "status": sub.status}), 409
    _message(sub, body)
    g.db.commit()
    return jsonify({"submission": _summary(sub)})


@bp.post("/submissions/<public_id>/reject")
@require_auth(role="moderator")
def reject(public_id: str):
    sub = _load(public_id)
    if sub is None:
        return jsonify({"error": "not_found"}), 404
    reason = ((request.get_json(silent=True) or {}).get("reason") or "").strip()
    try:
        transition(g.db, sub, "rejected", as_role=g.user.role, actor_user_id=g.user.id,
                   detail={"reason": reason})
    except InvalidTransition:
        return jsonify({"error": "submission.bad_state", "status": sub.status}), 409
    if reason:
        _message(sub, reason)
    sub.decided_by, sub.decided_at = g.user.id, utcnow()
    g.db.commit()
    return jsonify({"submission": _summary(sub)})


def _run_publish(sub: Submission):
    try:
        result = publish(
            g.db, sub,
            commons_repo=current_app.config["COMMONS_REPO_PATH"],
            lock_path=current_app.config["MEDIA_ROOT"].parent / "publish.lock",
            reviewed_by=g.user.handle,
        )
    except PublishBusy:
        return jsonify({"error": "publisher_busy"}), 409
    status = 200 if result["ok"] else 422
    return jsonify({"submission": _summary(sub), "publish": result}), status


@bp.post("/submissions/<public_id>/approve")
@require_auth(role="moderator")
def approve(public_id: str):
    sub = _load(public_id)
    if sub is None:
        return jsonify({"error": "not_found"}), 404
    try:
        transition(g.db, sub, "approved", as_role=g.user.role, actor_user_id=g.user.id)
    except InvalidTransition:
        return jsonify({"error": "submission.bad_state", "status": sub.status}), 409
    sub.decided_by, sub.decided_at = g.user.id, utcnow()
    g.db.commit()
    return _run_publish(sub)


@bp.post("/submissions/<public_id>/publish")
@require_auth(role="moderator")
def retry_publish(public_id: str):
    sub = _load(public_id)
    if sub is None:
        return jsonify({"error": "not_found"}), 404
    if sub.status not in ("approved", "publish_failed"):
        return jsonify({"error": "submission.bad_state", "status": sub.status}), 409
    return _run_publish(sub)


# --- reports lane (ADR-7) ---------------------------------------------------

@bp.get("/reports")
@require_auth(role="moderator")
def reports():
    status = request.args.get("status", "open")
    rows = g.db.execute(
        select(SiteReport, User.handle)
        .join(User, User.id == SiteReport.user_id)
        .where(SiteReport.status == status)
        .order_by(
            (SiteReport.category != "sensitive"),  # sensitive pinned first
            SiteReport.created_at,
        )
    ).all()
    return jsonify({"reports": [
        {"id": r.id, "site_id": r.site_id, "category": r.category, "body": r.body,
         "status": r.status, "reporter": handle, "created_at": r.created_at}
        for r, handle in rows
    ]})


@bp.post("/reports/<int:report_id>/<action>")
@require_auth(role="moderator")
def triage_report(report_id: int, action: str):
    if action not in ("resolve", "dismiss"):
        return jsonify({"error": "not_found"}), 404
    report = g.db.get(SiteReport, report_id)
    if report is None or report.status != "open":
        return jsonify({"error": "not_found"}), 404
    report.status = "resolved" if action == "resolve" else "dismissed"
    report.resolved_by = g.user.id
    report.resolved_at = utcnow()
    report.resolution_note = ((request.get_json(silent=True) or {}).get("note") or "").strip() or None
    g.db.commit()
    return jsonify({"ok": True, "status": report.status})
