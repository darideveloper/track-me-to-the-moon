from worktracker import store

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
