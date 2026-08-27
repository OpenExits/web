"""Panel configuration — everything env-overridable, sane local defaults."""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
VAR = BACKEND_ROOT / "openexit_panel" / "var"


class Config:
    SECRET_KEY = os.environ.get("OPENEXIT_SECRET_KEY", "dev-only-change-me")
    DB_URL = os.environ.get("OPENEXIT_DB_URL", f"sqlite:///{VAR / 'panel.sqlite3'}")
    COMMONS_REPO_PATH = Path(os.environ.get(
        "OPENEXIT_COMMONS_REPO", str(BACKEND_ROOT.parents[1] / "commons")))
    MEDIA_ROOT = Path(os.environ.get("OPENEXIT_MEDIA_ROOT", str(VAR / "media")))
    TERMS_VERSION = os.environ.get("OPENEXIT_TERMS_VERSION", "contributor-terms-2026-08")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # SESSION_COOKIE_SECURE is enabled by the prod entrypoint, not here (local http dev)
