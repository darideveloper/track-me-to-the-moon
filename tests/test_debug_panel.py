"""Debug panel: api emit, ring cap, per-type filter, manual actions, redaction."""
import pytest

from moon_tracker import api, debuglog, store, sync


@pytest.fixture(autouse=True)
def _clean_ring():
    debuglog.clear()
    yield
    debuglog.clear()


class _Resp:
    def __init__(self, status, body=None, text=None):
        self.status_code = status
        self._body = body
        self.text = text if text is not None else str(body)

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def _seed(con, n_act=3):
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    for i in range(n_act):
        store.add_activity(con, sid, f"2026-01-01T00:00:{i:02d}+00:00", "A", f"t{i}", 0)
    for k, v in (("api_base", "https://api.example.com"), ("api_token", "sekret-token"),
                 ("user_id", "u")):
        store.set_setting(con, k, v)
    return sid


def test_emit_on_ok(monkeypatch):
    monkeypatch.setattr(
        api.requests, "post", lambda *a, **k: _Resp(200, {"ok": True, "accepted": ["a:1"]}))
    events = []
    r = api.post_activities("https://x", "sekret-token", [{"client_id": "a:1"}],
                            emit=events.append)
    assert r.ok
    assert len(events) == 1
    e = events[0]
    assert e.method == "POST" and e.path == "/v1/activities" and e.status == 200
    assert e.ok is True and e.item_count == 1
    assert "sekret-token" not in e.req_preview + e.res_preview


def test_emit_on_401(monkeypatch):
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: _Resp(401, {"ok": False}))
    events = []
    r = api.post_activities("https://x", "t", [{"client_id": "a:1"}], emit=events.append)
    assert r.auth_error and r.error == "http 401"
    assert events[0].status == 401 and events[0].ok is False


def test_emit_on_timeout(monkeypatch):
    import requests as rq

    def _boom(*a, **k):
        raise rq.Timeout()

    monkeypatch.setattr(api.requests, "post", _boom)
    events = []
    r = api.post_sessions("https://x", "t", [{"client_id": "s:1"}], emit=events.append)
    assert r.retryable and r.error == "timeout" and r.status is None
    assert events[0].status is None and "timeout" in events[0].error


def test_truncation_marker():
    big = [{"client_id": f"a:{i}", "blob": "x" * 500} for i in range(50)]
    preview = api._preview_items(big, "")
    assert len(preview) <= api.REQ_PREVIEW_LIMIT + 60
    assert "truncated" in preview


def test_token_redacted_even_inside_payload():
    items = [{"client_id": "a:1", "title": "sekret-token leaked?"}]
    preview = api._preview_items(items, "sekret-token")
    assert "sekret-token" not in preview
    assert "REDACTED" in preview


def test_per_type_filter_leaves_others_pending(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 5)
    monkeypatch.setattr(api, "post_activities",
                        lambda b, t, items, emit=None: api.SyncResult(
                            ok=True, accepted_ids=[r["client_id"] for r in items]))
    stats = sync.drain(con, {}, reason="manual", tables={"activities"},
                       notify_fn=lambda *a: False, emit=lambda e: None)
    assert stats["sent_activities"] == 5
    assert stats["sent_sessions"] == 0
    assert store.pending_counts(con)["sessions"] == 1
    assert store.pending_counts(con)["activities"] == 0
    con.close()


def test_skipped_logs_event_without_base(tmp_path):
    con = store.connect(tmp_path / "t.db")
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    store.add_activity(con, sid, "2026-01-01T00:00:05+00:00", "A", "t", 0)
    events = []
    stats = sync.drain(con, {}, reason="manual", emit=events.append,
                       notify_fn=lambda *a: False)
    assert stats["skipped"] is True
    assert len(events) == 1 and "skipped" in events[0].error
    con.close()


def test_ring_cap_and_order():
    for i in range(250):
        debuglog.append(api.ApiEvent(ts=f"t{i}", method="POST", path="/v1/x",
                                    item_count=1, status=200, ok=True))
    items = debuglog.recent()
    assert len(items) == 200
    assert items[0].ts == "t249" and items[-1].ts == "t50"


def test_clear_never_touches_outbox(tmp_path):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 4)
    debuglog.append(api.ApiEvent(ts="t", method="POST", path="/v1/x", item_count=1))
    debuglog.clear()
    assert debuglog.recent() == []
    assert store.pending_counts(con)["activities"] == 4
    con.close()


def test_manual_screenshot_refuses_without_session(tmp_path):
    con = store.connect(tmp_path / "t.db")
    status, msg, stats = sync.manual_screenshot(con, {}, {"running": False, "sid": None})
    assert status == "refused" and stats is None
    con.close()


def test_manual_screenshot_attaches_to_last_while_stopped(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    sid = _seed(con, 0)
    shot = tmp_path / "fake.jpg"
    shot.write_text("x")
    monkeypatch.setattr("moon_tracker.shots.take", lambda d: shot)
    monkeypatch.setattr(api, "post_screenshot",
                        lambda b, t, m, p, emit=None: api.SyncResult(ok=True, accepted_ids=[m["client_id"]]))
    status, msg, stats = sync.manual_screenshot(con, {}, {"running": False, "sid": None},
                                                emit=lambda e: None)
    assert status == "ok"
    rows = con.execute("SELECT session_id FROM screenshots").fetchall()
    assert rows and rows[0][0] == sid
    assert store.pending_counts(con)["screenshots"] == 0
    con.close()


def test_test_connection_never_marks_uploaded(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 2)
    monkeypatch.setattr(api.requests, "get", lambda *a, **k: _Resp(200, {"ok": True}))
    events = []
    res = sync.test_connection(con, emit=events.append)
    assert res.ok
    assert store.pending_counts(con)["activities"] == 2
    assert any(e.path == "/health" for e in events)
    con.close()


def test_test_connection_falls_back_when_no_health(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 0)
    monkeypatch.setattr(api.requests, "get", lambda *a, **k: _Resp(404, {}))
    monkeypatch.setattr(api.requests, "post",
                        lambda *a, **k: _Resp(200, {"ok": True, "accepted": []}))
    events = []
    res = sync.test_connection(con, emit=events.append)
    assert res.ok
    assert [e.path for e in events] == ["/health", "/v1/sessions"]
    con.close()


def test_bundle_has_no_token(tmp_path):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 1)
    debuglog.append(api.ApiEvent(ts="2026-01-01T00:00:00+00:00", method="POST",
                                 path="/v1/activities", item_count=1, status=401,
                                 ok=False, error="http 401", auth="present"))
    bundle = debuglog.format_bundle("v1", store.pending_counts(con),
                                    store.last_sync(con), debuglog.recent())
    assert "sekret-token" not in bundle
    assert "pending:" in bundle
    con.close()
