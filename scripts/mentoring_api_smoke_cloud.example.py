#!/usr/bin/env python3
"""
Example launcher (safe to commit): copy to mentoring_api_smoke_cloud.py and fill secrets.

  copy scripts\\mentoring_api_smoke_cloud.example.py scripts\\mentoring_api_smoke_cloud.py

Then edit _DEFAULTS. mentoring_api_smoke_cloud.py is gitignored.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_DEFAULTS: dict[str, str] = {
    "USER_SERVICE_URL": "https://YOUR-USER-SERVICE.run.app",
    "MENTORING_BASE_URL": "https://YOUR-MENTORING-SERVICE.run.app",
    "JWT_SECRET": "REPLACE_ME",
    "INTERNAL_API_TOKEN": "REPLACE_ME",
    "NOTIFICATION_SERVICE_URL": "",
    "GAMIFICATION_SERVICE_URL": "",
    "AI_SERVICE_URL": "",
    "MENTEE_UI_URL": "",
    "COMMON_UI_URL": "",
}


def main() -> int:
    for key, value in _DEFAULTS.items():
        if value:
            os.environ.setdefault(key, value)
    here = Path(__file__).resolve().parent
    target = here / "mentoring_api_smoke_test.py"
    cmd = [sys.executable, str(target), *sys.argv[1:]]
    return int(subprocess.call(cmd))


if __name__ == "__main__":
    raise SystemExit(main())
