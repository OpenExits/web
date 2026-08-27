"""Bootstrap tool: promote a user by handle (the first admin has to come from
somewhere). Usage:

    python scripts/promote_user.py <handle> [user|moderator|admin]
"""
from __future__ import annotations

import sys

from openexit_panel.config import Config
from openexit_panel.db import init_engine, session
from openexit_panel.models import ROLES, User


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    handle = sys.argv[1]
    role = sys.argv[2] if len(sys.argv) > 2 else "moderator"
    if role not in ROLES:
        print(f"role must be one of {ROLES}")
        return 1
    init_engine(Config.DB_URL)
    db = session()
    try:
        user = db.query(User).filter_by(handle=handle).one_or_none()
        if user is None:
            print(f"no user with handle {handle!r}")
            return 1
        user.role = role
        db.commit()
        print(f"@{handle} is now {role}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
