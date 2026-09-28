import sqlite3
from worktracker import store


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
