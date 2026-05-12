from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str = ".env") -> None:
    """
    Minimal .env loader to avoid extra dependencies.
    - Ignores blank lines and comments
    - Loads KEY=VALUE pairs into process env if not already set
    """
    p = Path(path)
    if not p.exists():
        return

    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

