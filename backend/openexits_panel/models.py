"""Panel data model (FOUNDATION_PLAN §6.1 + ADR-7).

Conventions: all timestamps are UTC ISO-8601 TEXT; all *_json columns hold
canonical JSON as TEXT (engine-agnostic — no JSON1 operators in queries);
append-only tables (terms_acceptances, submission_events) are never updated
or deleted.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


ROLES = ("user", "moderator", "admin")

SUBMISSION_KINDS = ("new_site", "new_feature", "correction")
SUBMISSION_STATUSES = (
    "pending", "changes_requested", "approved", "publishing",
    "publish_failed", "published", "rejected", "withdrawn",
)

REPORT_CATEGORIES = ("position", "measurement", "access_status", "landing", "sensitive", "other")
REPORT_STATUSES = ("open", "resolved", "dismissed")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    handle: Mapped[str] = mapped_column(Text, unique=True)      # public; appears in provenance
    email: Mapped[str] = mapped_column(Text, unique=True)       # private: login + contact only
    password_hash: Mapped[str] = mapped_column(Text)            # argon2id
    role: Mapped[str] = mapped_column(Text, default="user")     # user | moderator | admin
    locale: Mapped[str] = mapped_column(Text, default="en")     # en | fr
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)


class TermsAcceptance(Base):
    """Append-only, legally load-bearing evidence. No IP stored by policy."""
    __tablename__ = "terms_acceptances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    terms_version: Mapped[str] = mapped_column(Text)
    accepted_at: Mapped[str] = mapped_column(Text, default=utcnow)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, unique=True)   # ULID; URLs + publisher branch names
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(Text)                     # new_site | new_feature | correction
    target_site_id: Mapped[str | None] = mapped_column(Text)    # "<country>/<slug>" for feature/correction
    payload_json: Mapped[str] = mapped_column(Text)             # contributor's words; never mutated after submit
    moderator_payload_json: Mapped[str | None] = mapped_column(Text)
    normalized_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending")
    machine_flags_json: Mapped[str] = mapped_column(Text, default="{}")
    terms_acceptance_id: Mapped[int] = mapped_column(ForeignKey("terms_acceptances.id"))
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[str | None] = mapped_column(Text)
    published_commit_sha: Mapped[str | None] = mapped_column(Text)
    published_site_id: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)
    updated_at: Mapped[str] = mapped_column(Text, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        Index("ix_submissions_status_created", "status", "created_at"),
        Index("ix_submissions_user", "user_id"),
    )


class SubmissionMessage(Base):
    __tablename__ = "submission_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(Text, default="public")  # public | moderator_only
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)


class SubmissionEvent(Base):
    """Append-only audit trail: every status change, edit, publish step."""
    __tablename__ = "submission_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # NULL = system/bot
    event: Mapped[str] = mapped_column(Text)
    from_status: Mapped[str | None] = mapped_column(Text)
    to_status: Mapped[str | None] = mapped_column(Text)
    detail_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)


class MediaUpload(Base):
    __tablename__ = "media_uploads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sha256: Mapped[str] = mapped_column(Text, unique=True)      # hash of the PROCESSED bytes
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    uploader_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    original_filename: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    caption: Mapped[str | None] = mapped_column(Text)
    licence: Mapped[str] = mapped_column(Text, default="CC-BY-SA-4.0")
    storage_path: Mapped[str] = mapped_column(Text)             # relative to MEDIA_ROOT
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)


# --- ADR-7 community layer (panel-only; never enters the commons) -----------

class SiteComment(Base):
    __tablename__ = "site_comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[str] = mapped_column(Text)                  # OpenExits site id (ULID)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)
    deleted_at: Mapped[str | None] = mapped_column(Text)        # soft delete
    deleted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (Index("ix_site_comments_site_created", "site_id", "created_at"),)


class SiteConfirmation(Base):
    """'Checked out for me' — one live row per (site, user); re-confirm updates."""
    __tablename__ = "site_confirmations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    confirmed_on: Mapped[str] = mapped_column(Text)             # date (YYYY-MM-DD)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)
    updated_at: Mapped[str] = mapped_column(Text, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        UniqueConstraint("site_id", "user_id", name="uq_confirmation_site_user"),
        Index("ix_confirmations_site_date", "site_id", "confirmed_on"),
    )


class SiteReport(Base):
    """'Report a problem' — a moderation ticket, category required."""
    __tablename__ = "site_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(Text)                 # REPORT_CATEGORIES
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="open")   # open | resolved | dismissed
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[str | None] = mapped_column(Text)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)
    __table_args__ = (
        Index("ix_site_reports_status_created", "status", "created_at"),
        Index("ix_site_reports_site", "site_id"),
    )
