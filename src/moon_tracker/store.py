"""SQLite store: sessions, activities, screenshots outbox."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT,
  uploaded INTEGER DEFAULT 0, upload_attempts INTEGER DEFAULT 0, last_error TEXT DEFAULT '', uploaded_at TEXT);
CREATE TABLE IF NOT EXISTS activities(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, ts TEXT NOT NULL, app TEXT, title TEXT, idle INTEGER DEFAULT 0,
  uploaded INTEGER DEFAULT 0, upload_attempts INTEGER DEFAULT 0, last_error TEXT DEFAULT '', uploaded_at TEXT);
CREATE TABLE IF NOT EXISTS screenshots(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, ts TEXT NOT NULL, path TEXT NOT NULL,
  uploaded INTEGER DEFAULT 0, upload_attempts INTEGER DEFAULT 0, last_error TEXT DEFAULT '', uploaded_at TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS sync_runs(id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT NOT NULL,
  reason TEXT DEFAULT '', sent_sessions INTEGER DEFAULT 0, sent_activities INTEGER DEFAULT 0, sent_screenshots INTEGER DEFAULT 0, error TEXT DEFAULT '');
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_sessions_pending ON sessions(uploaded, id);
CREATE INDEX IF NOT EXISTS idx_activities_pending ON activities(uploaded, id);
CREATE INDEX IF NOT EXISTS idx_screenshots_pending ON screenshots(uploaded, id);
CREATE INDEX IF NOT EXISTS idx_screenshots_uploaded_at ON screenshots(uploaded, uploaded_at);
"""

SETTINGS_KEYS = frozenset({"api_base", "api_token", "user_id"})

_OUTBOX_TABLES = frozenset({"sessions", "activities", "screenshots"})

# ponytail: single lock for the shared connection (collector + sync threads).
_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _columns(con: sqlite3.Connection, table: str) -> set[str]:
    with _LOCK:
        return {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate(con: sqlite3.Connection) -> None:
    """Idempotent migration for pre-outbox DBs: add columns, create ledger + indexes."""
    with _LOCK:
        existing = {
            r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        for table in ("sessions", "activities", "screenshots"):
            if table not in existing:
                continue  # created by SCHEMA above with new columns
            cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
            for col, ddl in (
                ("uploaded", "INTEGER DEFAULT 0"),
                ("upload_attempts", "INTEGER DEFAULT 0"),
                ("last_error", "TEXT DEFAULT ''"),
                ("uploaded_at", "TEXT"),
            ):
                if col not in cols:
                    try:
                        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                    except Exception:
                        pass
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS sync_runs(id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT NOT NULL,
              reason TEXT DEFAULT '', sent_sessions INTEGER DEFAULT 0, sent_activities INTEGER DEFAULT 0, sent_screenshots INTEGER DEFAULT 0, error TEXT DEFAULT '');
            """
        )
        con.executescript(INDEXES)
        try:
            # Backfill: sessions closed after a mid-run tick were marked
            # uploaded=1 with ended_at set, so close flush never resent them.
            con.execute(
                "UPDATE sessions SET uploaded=0 WHERE uploaded=1 AND ended_at IS NOT NULL"
            )
        except Exception:
            pass
        con.commit()


def connect(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db), check_same_thread=False)
    with _LOCK:
        con.executescript(SCHEMA)
    _migrate(con)
    with _LOCK:
        con.executescript(INDEXES)
    return con


def start_session(con: sqlite3.Connection, ts: str) -> int:
    with _LOCK:
        cur = con.execute("INSERT INTO sessions(started_at) VALUES (?)", (ts,))
        sid = cur.lastrowid
        # ponytail: one shared sessions table, a new Launch ends crash orphans
        con.execute(
            "UPDATE sessions SET ended_at=?, uploaded=0 WHERE ended_at IS NULL AND id != ?",
            (ts, sid),
        )
        con.commit()
        return sid


def end_session(con: sqlite3.Connection, sid: int, ts: str) -> None:
    with _LOCK:
        con.execute("UPDATE sessions SET ended_at=?, uploaded=0 WHERE id=?", (ts, sid))
        con.commit()


def add_activity(con: sqlite3.Connection, sid: int, ts: str, app: str, title: str, idle: int) -> None:
    with _LOCK:
        con.execute(
            "INSERT INTO activities(session_id, ts, app, title, idle) VALUES (?,?,?,?,?)",
            (sid, ts, app[:200], title[:500], idle),
        )
        con.commit()


def add_screenshot(con: sqlite3.Connection, sid: int, ts: str, path: str) -> None:
    with _LOCK:
        con.execute("INSERT INTO screenshots(session_id, ts, path) VALUES (?,?,?)", (sid, ts, path))
        con.commit()


def list_sessions(con: sqlite3.Connection, limit: int = 10):
    with _LOCK:
        return con.execute(
            "SELECT id, started_at, ended_at, uploaded FROM sessions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()


def pending_sessions(con: sqlite3.Connection, limit: int = 100):
    with _LOCK:
        return con.execute(
            "SELECT id, started_at, ended_at FROM sessions WHERE uploaded=0 ORDER BY id ASC LIMIT ?",
            (limit,),
        ).fetchall()


def pending_screenshots(con: sqlite3.Connection, limit: int = 20):
    with _LOCK:
        return con.execute(
            "SELECT id, session_id, ts, path FROM screenshots WHERE uploaded=0 ORDER BY id ASC LIMIT ?",
            (limit,),
        ).fetchall()


def pending_activities(con: sqlite3.Connection, limit: int = 100):
    with _LOCK:
        return con.execute(
            "SELECT id, session_id, ts, app, title, idle FROM activities WHERE uploaded=0 ORDER BY id ASC LIMIT ?",
            (limit,),
        ).fetchall()


def pending_counts(con: sqlite3.Connection) -> dict:
    with _LOCK:
        out = {}
        for table in ("sessions", "activities", "screenshots"):
            try:
                out[table] = con.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE uploaded=0"
                ).fetchone()[0]
            except Exception:
                out[table] = 0
        return out


def mark_uploaded(con: sqlite3.Connection, table: str, ids: list[int]) -> None:
    if table not in _OUTBOX_TABLES or not ids:
        return
    with _LOCK:
        q = ",".join("?" for _ in ids)
        con.execute(
            f"UPDATE {table} SET uploaded=1, uploaded_at=?, last_error='' WHERE id IN ({q})",
            (_now(), *ids),
        )
        con.commit()


def note_error(con: sqlite3.Connection, table: str, ids: list[int], err: str) -> None:
    if table not in _OUTBOX_TABLES or not ids:
        return
    with _LOCK:
        q = ",".join("?" for _ in ids)
        con.execute(
            f"UPDATE {table} SET upload_attempts=upload_attempts+1, last_error=? WHERE id IN ({q})",
            ((err or "")[:500], *ids),
        )
        con.commit()


def log_sync_run(
    con: sqlite3.Connection,
    started_at: str,
    reason: str,
    sent_sessions: int = 0,
    sent_activities: int = 0,
    sent_screenshots: int = 0,
    error: str = "",
) -> None:
    with _LOCK:
        con.execute(
            "INSERT INTO sync_runs(started_at, finished_at, reason, sent_sessions, sent_activities, sent_screenshots, error)"
            " VALUES (?,?,?,?,?,?,?)",
            (started_at, _now(), reason, sent_sessions, sent_activities, sent_screenshots, (error or "")[:1000]),
        )
        con.commit()


def last_sync(con: sqlite3.Connection):
    with _LOCK:
        try:
            return con.execute(
                "SELECT started_at, finished_at, reason, sent_sessions, sent_activities, sent_screenshots, error"
                " FROM sync_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        except Exception:
            return None


def uploaded_screenshots_before(con: sqlite3.Connection, cutoff: str, limit: int = 100):
    """Acked shots ready for retention cleanup."""
    with _LOCK:
        return con.execute(
            "SELECT id, path FROM screenshots WHERE uploaded=1 AND uploaded_at IS NOT NULL"
            " AND uploaded_at < ? ORDER BY uploaded_at ASC LIMIT ?",
            (cutoff, limit),
        ).fetchall()


def delete_screenshot_row(con: sqlite3.Connection, sid: int) -> None:
    with _LOCK:
        con.execute("DELETE FROM screenshots WHERE id=?", (sid,))
        con.commit()


def mark_screenshot_uploaded(con: sqlite3.Connection, sid: int) -> None:
    mark_uploaded(con, "screenshots", [sid])


def _is_internal_key(key: str) -> bool:
    return key.startswith("last_notify_")


def get_setting(con: sqlite3.Connection, key: str) -> str:
    if key not in SETTINGS_KEYS and not _is_internal_key(key):
        raise ValueError(f"unknown setting: {key!r}")
    with _LOCK:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else ""


def set_setting(con: sqlite3.Connection, key: str, value: str) -> None:
    if key not in SETTINGS_KEYS and not _is_internal_key(key):
        raise ValueError(f"unknown setting: {key!r}")
    with _LOCK:
        con.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value.strip()),
        )
        con.commit()


def get_settings_dict(con: sqlite3.Connection) -> dict:
    return {k: get_setting(con, k) for k in sorted(SETTINGS_KEYS)}


def validate_settings(s: dict) -> dict[str, str]:
    """Return {key: error} for invalid identity/API settings (empty = valid)."""
    from urllib.parse import urlparse

    errors: dict[str, str] = {}
    base = s.get("api_base", "").strip()
    u = urlparse(base)
    if u.scheme not in ("http", "https") or not u.netloc:
        errors["api_base"] = "must be an http(s) URL"
    if not s.get("api_token", "").strip():
        errors["api_token"] = "required"
    if not s.get("user_id", "").strip():
        errors["user_id"] = "required"
    return errors
