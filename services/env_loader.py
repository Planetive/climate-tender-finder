"""
Load key=value pairs from a local .env file into os.environ.

Why: avoid requiring python-dotenv; keeps beginner setup simple.
Does not overwrite variables already set in the real environment.
"""
import os
from pathlib import Path
from typing import Optional


def load_env_file(path: Optional[str] = None) -> None:
    """Read project-root .env (if present) and set missing env vars."""
    env_path = Path(path) if path else Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return

    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"⚠ Could not read .env: {e}")
        return

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        # Do not override real environment / Docker / CI vars
        if key not in os.environ or os.environ.get(key, "") == "":
            os.environ[key] = value
