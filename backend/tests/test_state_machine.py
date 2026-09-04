"""Submission status transitions: allowed paths, role enforcement, event log."""
from __future__ import annotations

import pytest

from openexits_panel.db import session as db_session
from openexits_panel.models import Submission, SubmissionEvent, TermsAcceptance, User
from openexits_panel.services.state_machine import InvalidTransition, transition


@pytest.fixture()
def sub(app):
    with app.app_context():
        db = db_session()
        try:
            user = User(handle="s_user", email="s@example.invalid", password_hash="x")
            db.add(user)
            db.flush()
            terms = TermsAcceptance(user_id=user.id, terms_version="contributor-terms-2026-08")
            db.add(terms)
            db.flush()
            s = Submission(public_id="01J9TESTSUBAAAAAAAAAAAAAAA", user_id=user.id,
                           kind="new_site", payload_json="{}", terms_acceptance_id=terms.id)
            db.add(s)
            db.commit()
            yield db, s
        finally:
            db.close()


def test_happy_path_to_published(sub):
    db, s = sub
    transition(db, s, "approved", as_role="moderator", actor_user_id=None)
    transition(db, s, "publishing", as_role="system")
    transition(db, s, "published", as_role="system")
    db.commit()
    assert s.status == "published"
    events = db.query(SubmissionEvent).filter_by(submission_id=s.id).all()
    assert [(e.from_status, e.to_status) for e in events] == [
        ("pending", "approved"), ("approved", "publishing"), ("publishing", "published"),
    ]


def test_failure_and_retry_path(sub):
    db, s = sub
    transition(db, s, "approved", as_role="admin")          # admin counts as moderator
    transition(db, s, "publishing", as_role="system")
    transition(db, s, "publish_failed", as_role="system", detail={"gate": "OE-R11"})
    transition(db, s, "publishing", as_role="system")       # retry
    transition(db, s, "published", as_role="system")
    assert s.status == "published"


def test_owner_cannot_approve(sub):
    db, s = sub
    with pytest.raises(InvalidTransition):
        transition(db, s, "approved", as_role="owner")


def test_no_transition_from_terminal(sub):
    db, s = sub
    transition(db, s, "rejected", as_role="moderator")
    with pytest.raises(InvalidTransition):
        transition(db, s, "pending", as_role="owner")


def test_resubmit_cycle(sub):
    db, s = sub
    transition(db, s, "changes_requested", as_role="moderator")
    transition(db, s, "pending", as_role="owner")
    assert s.status == "pending"
