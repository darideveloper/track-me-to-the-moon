from moon_tracker import store

import pytest


def test_session_roundtrip(tmp_path):
    con = store.connect(tmp_path / "t.db")
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    store.add_activity(con, sid, "2026-01-01T00:00:05+00:00", "Code", "main.py", 0)
    store.add_screenshot(con, sid, "2026-01-01T00:05:00+00:00", "/tmp/x.jpg")
    assert store.pending_screenshots(con)
    store.mark_screenshot_uploaded(con, 1)
    assert not store.pending_screenshots(con)
    store.end_session(con, sid, "2026-01-01T01:00:00+00:00")
    con.close()


def test_list_sessions_newest_first(tmp_path):
    con = store.connect(tmp_path / "t.db")
    s1 = store.start_session(con, "2026-01-01T09:00:00+00:00")
    store.end_session(con, s1, "2026-01-01T10:30:00+00:00")
    s2 = store.start_session(con, "2026-01-01T11:00:00+00:00")
    store.end_session(con, s2, "2026-01-01T11:45:00+00:00")
    rows = store.list_sessions(con, 10)
    assert [r[0] for r in rows] == [s2, s1]
    assert rows[0][1] == "2026-01-01T11:00:00+00:00"
    con.close()


def test_list_sessions_open_session(tmp_path):
    con = store.connect(tmp_path / "t.db")
    sid = store.start_session(con, "2026-01-01T13:00:00+00:00")
    rows = store.list_sessions(con, 10)
    assert len(rows) == 1
    assert rows[0][0] == sid
    assert rows[0][2] is None  # ended_at NULL while recording
    assert store.list_sessions(con, 1) == rows
    con.close()


def test_settings_table_autocreates_on_old_db(tmp_path):
    import sqlite3

    db = tmp_path / "old.db"  # pre-settings schema: sessions only
    con0 = sqlite3.connect(str(db))
    con0.execute("CREATE TABLE sessions(id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT)")
    con0.execute("INSERT INTO sessions(started_at) VALUES ('2026-01-01T00:00:00+00:00')")
    con0.commit()
    con0.close()
    con = store.connect(db)
    assert store.get_settings_dict(con) == {"api_base": "", "api_token": "", "user_id": ""}
    assert con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    con.close()


def test_settings_roundtrip_trims(tmp_path):
    con = store.connect(tmp_path / "t.db")
    store.set_setting(con, "user_id", "  emp-042  ")
    assert store.get_setting(con, "user_id") == "emp-042"
    store.set_setting(con, "user_id", "emp-043")
    assert store.get_setting(con, "user_id") == "emp-043"
    con.close()


def test_settings_missing_key_reads_empty(tmp_path):
    con = store.connect(tmp_path / "t.db")
    assert store.get_setting(con, "api_token") == ""
    con.close()


def test_settings_unknown_key_rejected(tmp_path):
    con = store.connect(tmp_path / "t.db")
    with pytest.raises(ValueError):
        store.set_setting(con, "nope", "x")
    with pytest.raises(ValueError):
        store.get_setting(con, "nope")
    con.close()


def test_validate_settings(tmp_path):
    assert store.validate_settings(
        {"api_base": "https://api.example.com", "api_token": "s", "user_id": "e"}) == {}
    bad = store.validate_settings({"api_base": "not-a-url", "api_token": " ", "user_id": ""})
    assert set(bad) == {"api_base", "api_token", "user_id"}


def test_migration_idempotent_on_new_and_old_db(tmp_path):
    import sqlite3

    db = tmp_path / "mig.db"
    con = store.connect(db)
    con.close()
    con = store.connect(db)  # second connect must not fail
    cols = {r[1] for r in con.execute("PRAGMA table_info(activities)").fetchall()}
    assert {"uploaded", "upload_attempts", "last_error", "uploaded_at"} <= cols
    assert con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sync_runs'"
    ).fetchone()
    con.close()
    # pre-outbox schema without new columns
    db2 = tmp_path / "old2.db"
    c0 = sqlite3.connect(str(db2))
    c0.execute("CREATE TABLE sessions(id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT)")
    c0.execute("CREATE TABLE activities(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, ts TEXT NOT NULL, app TEXT, title TEXT, idle INTEGER DEFAULT 0)")
    c0.execute("CREATE TABLE screenshots(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, ts TEXT NOT NULL, path TEXT NOT NULL, uploaded INTEGER DEFAULT 0)")
    c0.execute("CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '')")
    c0.commit()
    c0.close()
    con2 = store.connect(db2)
    assert store.pending_activities(con2, 10) == []
    con2.close()


def test_concurrent_collect_and_mark(tmp_path):
    import threading

    con = store.connect(tmp_path / "t.db")
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    for i in range(50):
        store.add_activity(con, sid, f"2026-01-01T00:00:{i:02d}+00:00", "A", "t", 0)
    errors = []

    def _collect():
        try:
            for i in range(100):
                store.add_activity(con, sid, "2026-01-01T00:01:00+00:00", "B", "x", 0)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    def _mark():
        try:
            for _ in range(20):
                rows = store.pending_activities(con, 10)
                if rows:
                    store.mark_uploaded(con, "activities", [r[0] for r in rows])
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=_collect) for _ in range(3)]
    threads += [threading.Thread(target=_mark) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    total = con.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    assert total == 350
    con.close()


def test_pending_oldest_first_and_mark_subset(tmp_path):
    con = store.connect(tmp_path / "t.db")
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    for i in range(5):
        store.add_activity(con, sid, f"2026-01-01T00:00:0{i}+00:00", "A", f"t{i}", 0)
    rows = store.pending_activities(con, 3)
    assert [r[0] for r in rows] == [1, 2, 3]
    store.mark_uploaded(con, "activities", [1, 2])  # partial ack subset
    assert [r[0] for r in store.pending_activities(con, 10)] == [3, 4, 5]
    store.note_error(con, "activities", [3], "timeout")
    row = con.execute("SELECT upload_attempts, last_error, uploaded FROM activities WHERE id=3").fetchone()
    assert row[0] == 1 and row[1] == "timeout" and row[2] == 0
    # sessions pending incl. open session
    assert [(r[0], r[2]) for r in store.pending_sessions(con, 10)] == [(sid, None)]
    store.mark_uploaded(con, "sessions", [sid])
    assert store.pending_sessions(con, 10) == []
    con.close()
