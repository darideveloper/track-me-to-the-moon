"""SQLite store: sessions, activities, screenshots outbox."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT);
CREATE TABLE IF NOT EXISTS activities(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, ts TEXT NOT NULL, app TEXT, title TEXT, idle INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS screenshots(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, ts TEXT NOT NULL, path TEXT NOT NULL, uploaded INTEGER DEFAULT 0);
"""

def connect(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db), check_same_thread=False)
    con.executescript(SCHEMA)
    return con

def start_session(con: sqlite3.Connection, ts: str) -> int:
    cur = con.execute("INSERT INTO sessions(started_at) VALUES (?)", (ts,))
    con.commit()
    return cur.lastrowid

def end_session(con: sqlite3.Connection, sid: int, ts: str) -> None:
    con.execute("UPDATE sessions SET ended_at=? WHERE id=?", (ts, sid))
    con.commit()

def add_activity(con: sqlite3.Connection, sid: int, ts: str, app: str, title: str, idle: int) -> None:
    con.execute(
        "INSERT INTO activities(session_id, ts, app, title, idle) VALUES (?,?,?,?,?)",
        (sid, ts, app[:200], title[:500], idle),
    )
    con.commit()

def add_screenshot(con: sqlite3.Connection, sid: int, ts: str, path: str) -> None:
    con.execute("INSERT INTO screenshots(session_id, ts, path) VALUES (?,?,?)", (sid, ts, path))
    con.commit()

def list_sessions(con: sqlite3.Connection, limit: int = 10):
    return con.execute(
        "SELECT id, started_at, ended_at FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()


def pending_screenshots(con: sqlite3.Connection, limit: int = 20):
    return con.execute(
        "SELECT id, session_id, ts, path FROM screenshots WHERE uploaded=0 ORDER BY id LIMIT ?", (limit,)
    ).fetchall()

def pending_activities(con: sqlite3.Connection, limit: int = 200):
    return con.execute(
        "SELECT id, session_id, ts, app, title, idle FROM activities WHERE id NOT IN (SELECT id FROM synced_activities) ORDER BY id LIMIT ?",
        (limit,),
    ) if _has_synced(con) else con.execute(
        "SELECT id, session_id, ts, app, title, idle FROM activities ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()

def _has_synced(con: sqlite3.Connection) -> bool:
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='synced_activities'"
    ).fetchone() is not None

def mark_screenshot_uploaded(con: sqlite3.Connection, sid: int) -> None:
    con.execute("UPDATE screenshots SET uploaded=1 WHERE id=?", (sid,))
    con.commit()
