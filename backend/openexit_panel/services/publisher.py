"""The publisher bot (ADR-4, FOUNDATION_PLAN §7).

Synchronous, file-locked, plain `git` via subprocess. Invariant: main only
moves on a fully-gated merge; every failure leaves the repo exactly as found.

Steps: preflight -> branch sub/<public_id> -> materialize (bot-stamped
provenance, media refs) -> ci/run_gates.py (the same entry point future GH
Actions calls) -> commit with machine-parseable trailers -> merge --no-ff ->
rebuild build/ -> record. Failure: branch force-deleted, tree restored,
submission -> publish_failed with the full gate report.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# gate/build subprocesses must not litter the repo with .pyc caches — the
# preflight treats any untracked file as a dirty tree
_SUBPROCESS_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}

from filelock import FileLock, Timeout
from sqlalchemy import select

from openexit_validator.normalize import read_json, slugify, write_json

from ..models import MediaUpload, Submission, SubmissionEvent, User, utcnow
from . import nearby
from .state_machine import transition

BOT_NAME = "OpenExit Bot"
BOT_EMAIL = "bot@openexit.invalid"  # set the real address before hosting


class PublishBusy(Exception):
    pass


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, encoding="utf-8",
        env={**_SUBPROCESS_ENV,
             "GIT_AUTHOR_NAME": BOT_NAME, "GIT_AUTHOR_EMAIL": BOT_EMAIL,
             "GIT_COMMITTER_NAME": BOT_NAME, "GIT_COMMITTER_EMAIL": BOT_EMAIL},
    )


def _default_branch(repo: Path) -> str:
    return _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "master"


def _stamped_provenance_entry(sub: Submission, contributor: str, reviewed_by: str) -> dict:
    return {
        "source": "panel",
        "sourceId": sub.public_id,
        "contributor": contributor,
        "contributedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "licence": "ODbL-1.0",
        "reviewedBy": reviewed_by,     # extension field; preserved by rule OE-R13
    }


def _site_relpath(doc: dict, sub: Submission) -> str:
    if sub.kind in ("new_feature", "correction") and sub.target_site_id:
        return f"sites/{sub.target_site_id}.json"
    return f"sites/{doc['country'].lower()}/{slugify(doc['name'])}.json"


def _materialize(db, repo: Path, sub: Submission, doc: dict,
                 contributor: str, reviewed_by: str) -> str:
    """Stamp provenance + media refs, write the canonical file. Returns relpath."""
    stamped = _stamped_provenance_entry(sub, contributor, reviewed_by)
    relpath = _site_relpath(doc, sub)
    target = repo / relpath
    if sub.kind == "new_site":
        if target.exists():
            raise PublishError("slug_collision", f"{relpath} already exists — rename the site")
        doc["provenance"] = [stamped]
    else:
        if not target.exists():
            raise PublishError("target_missing", f"{relpath} not found at HEAD")
        head_prov = read_json(target).get("provenance", [])
        doc["provenance"] = head_prov + [stamped]

    media_rows = db.execute(
        select(MediaUpload).where(MediaUpload.submission_id == sub.id)
    ).scalars().all()
    if media_rows:
        existing = doc.get("media", [])
        known = {m.get("sha256") for m in existing}
        for m in media_rows:
            if m.sha256 not in known:
                existing.append({
                    "role": "overview", "sha256": m.sha256, "urls": [],
                    "licence": m.licence, "contributor": contributor,
                    **({"caption": m.caption} if m.caption else {}),
                })
        doc["media"] = existing

    doc["updatedAt"] = utcnow()
    write_json(target, doc)
    return relpath


class PublishError(Exception):
    def __init__(self, key: str, detail: str = ""):
        super().__init__(f"{key}: {detail}")
        self.key = key
        self.detail = detail


def _event(db, sub: Submission, event: str, detail: dict | None = None) -> None:
    db.add(SubmissionEvent(
        submission_id=sub.id, actor_user_id=None, event=event,
        detail_json=json.dumps(detail, ensure_ascii=False, sort_keys=True) if detail else None,
    ))


def publish(db, sub: Submission, *, commons_repo: Path, lock_path: Path,
            reviewed_by: str) -> dict:
    """Publish an approved submission. Returns {'ok': bool, 'report': str, ...};
    commits DB state itself (status transitions must survive the request)."""
    lock = FileLock(str(lock_path))
    try:
        lock.acquire(timeout=0)
    except Timeout:
        raise PublishBusy()

    branch = f"sub/{sub.public_id}"
    base = _default_branch(commons_repo)
    contributor = db.get(User, sub.user_id).handle
    try:
        transition(db, sub, "publishing", as_role="system")
        db.commit()

        # 1. preflight: never publish onto a dirty tree
        dirty = _git(commons_repo, "status", "--porcelain").stdout.strip()
        if dirty:
            raise PublishError("repo_dirty", dirty[:400])

        doc = json.loads(sub.normalized_json)

        try:
            # 2-3. branch + materialize
            _git(commons_repo, "checkout", "-q", "-b", branch)
            relpath = _materialize(db, commons_repo, sub, doc, contributor, reviewed_by)

            # 4. gates — the same script the commons CI runs
            gates = subprocess.run(
                [sys.executable, str(commons_repo / "ci" / "run_gates.py"),
                 "--repo", str(commons_repo), "--changed", relpath, "--base", base],
                capture_output=True, encoding="utf-8", env=_SUBPROCESS_ENV,
            )
            if gates.returncode != 0:
                report = (gates.stdout + ("\n" + gates.stderr if gates.stderr else ""))
                raise PublishError("gates_failed", report[-3000:])

            # 5. commit with trailers
            verb = "add" if sub.kind == "new_site" else "update"
            site_path = relpath.removeprefix("sites/").removesuffix(".json")
            message = (
                f"site: {verb} {site_path}\n\n"
                f"Submission: {sub.public_id}\n"
                f"Contributor: {contributor}\n"
                f"Reviewed-by: {reviewed_by}\n"
                f"Source: panel\n"
            )
            _git(commons_repo, "add", "-A")
            _git(commons_repo, "commit", "-q", "-m", message)

            # 6. merge --no-ff: one merge commit per submission
            _git(commons_repo, "checkout", "-q", base)
            _git(commons_repo, "merge", "-q", "--no-ff", "-m",
                 f"merge: {verb} {site_path} ({sub.public_id})", branch)
            merge_sha = _git(commons_repo, "rev-parse", "HEAD").stdout.strip()
            _git(commons_repo, "branch", "-q", "-d", branch)
        except PublishError:
            _abort(commons_repo, base, branch)
            raise
        except subprocess.CalledProcessError as exc:
            _abort(commons_repo, base, branch)
            raise PublishError("git_failed", (exc.stderr or str(exc))[:800])

        # 7. rebuild artifacts on main (locally the bot does both; on GitHub
        #    this step moves to the post-merge Action)
        build = subprocess.run(
            [sys.executable, str(commons_repo / "scripts" / "build_artifacts.py"),
             "--repo", str(commons_repo)],
            capture_output=True, encoding="utf-8", env=_SUBPROCESS_ENV,
        )
        if build.returncode != 0:
            raise PublishError("build_failed", (build.stdout + build.stderr)[-2000:])
        if _git(commons_repo, "status", "--porcelain").stdout.strip():
            _git(commons_repo, "add", "build/")
            _git(commons_repo, "commit", "-q", "-m",
                 f"chore(build): regenerate for {merge_sha[:10]}")

        # 8. record
        transition(db, sub, "published", as_role="system")
        sub.published_commit_sha = merge_sha
        sub.published_site_id = site_path
        sub.published_at = utcnow()
        for m in db.execute(select(MediaUpload)
                            .where(MediaUpload.submission_id == sub.id)).scalars():
            m.published = True
        _event(db, sub, "published", {"sha": merge_sha, "path": site_path})
        db.commit()
        nearby.invalidate()
        return {"ok": True, "sha": merge_sha, "site": site_path}

    except PublishError as exc:
        transition(db, sub, "publish_failed", as_role="system",
                   detail={"key": exc.key, "detail": exc.detail})
        db.commit()
        return {"ok": False, "key": exc.key, "report": exc.detail}
    finally:
        lock.release()


def _abort(repo: Path, base: str, branch: str) -> None:
    """Restore a clean tree on the base branch; nothing half-lands."""
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-f", base],
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "branch", "-q", "-D", branch],
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "clean", "-qfd", "sites", "routes"],
                   capture_output=True)


def tag_release(commons_repo: Path, tag: str) -> str:
    if not tag.startswith("data/"):
        raise PublishError("bad_tag", "release tags are data/YYYY.MM.N")
    _git(commons_repo, "tag", "-a", tag, "-m", f"chore(release): {tag}")
    return tag
