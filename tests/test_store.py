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
