"""Submission status transitions — every change goes through transition(),
every change writes a submission_events row (FOUNDATION_PLAN §6.2).

Roles: 'owner' = the submitting contributor; 'moderator' includes admin;
'system' = the publisher bot.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models import Submission, SubmissionEvent

# (from, to) -> role allowed to make this transition
TRANSITIONS: dict[tuple[str, str], str] = {
    ("pending", "changes_requested"): "moderator",
    ("pending", "rejected"): "moderator",
    ("pending", "approved"): "moderator",
    ("pending", "withdrawn"): "owner",
    ("changes_requested", "pending"): "owner",        # resubmit
    ("changes_requested", "withdrawn"): "owner",
    ("approved", "publishing"): "system",
    ("publish_failed", "publishing"): "system",       # retry
    ("publishing", "published"): "system",
    ("publishing", "publish_failed"): "system",
}

# Moderator field edits are allowed only in these states
EDITABLE_STATES = ("pending", "publish_failed")


class InvalidTransition(Exception):
    pass


def transition(db: Session, sub: Submission, to: str, *, as_role: str,
               actor_user_id: int | None = None, detail: dict | None = None) -> None:
    """Move sub.status -> to if (from, to, role) is allowed; log the event.
    Caller commits."""
    allowed = TRANSITIONS.get((sub.status, to))
    if allowed is None:
        raise InvalidTransition(f"{sub.status} -> {to} is not a transition")
    if not _role_ok(allowed, as_role):
        raise InvalidTransition(f"{sub.status} -> {to} requires {allowed}, got {as_role}")
    frm = sub.status
    sub.status = to
    db.add(SubmissionEvent(
        submission_id=sub.id, actor_user_id=actor_user_id, event="status_changed",
        from_status=frm, to_status=to,
        detail_json=json.dumps(detail, ensure_ascii=False, sort_keys=True) if detail else None,
    ))


def _role_ok(required: str, actual: str) -> bool:
    if required == "moderator":
        return actual in ("moderator", "admin")
    return actual == required
