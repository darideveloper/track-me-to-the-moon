"""Runtime version string from git (branch@hash date), fallback to unknown."""
from __future__ import annotations

import subprocess
from pathlib import Path


def _repo_root() -> Path | None:
    try:
        root = Path(__file__).resolve().parents[2]
        if (root / ".git").exists():
            return root
    except Exception:
        pass
    return None


def _git(*args: str) -> str | None:
    root = _repo_root()
    if root is None:
        return None
    try:
        out = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except Exception:
        pass
    return None


def get_version() -> str:
    """Return `<branch>@<short-hash> <date>` or `unknown` outside git."""
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    commit = _git("rev-parse", "--short", "HEAD")
    stamp = _git("log", "-1", "--format=%ci")
    if branch and commit:
        date = stamp[:10] if stamp else ""
        return f"{branch}@{commit} {date}".strip()
    return "unknown"
