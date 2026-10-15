import threading
import time

from moon_tracker import api, store, sync
from moon_tracker.sync import cleanup_screenshots


def _seed(con, n_act=250, n_shots=0, tmp_path=None):
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    for i in range(n_act):
        store.add_activity(con, sid, f"2026-01-01T00:00:{i:02d}+00:00", "A", f"t{i}", 0)
    for i in range(n_shots):
        p = str(tmp_path / f"s{i}.jpg") if tmp_path else f"/tmp/s{i}.jpg"
        if tmp_path:
            open(p, "w").write("x")
        store.add_screenshot(con, sid, "2026-01-01T00:05:00+00:00", p)
    for k, v in (("api_base", "https://api.example.com"), ("api_token", "t"), ("user_id", "u")):
        store.set_setting(con, k, v)
    return sid


def _ok_all(items):
    ids = [r["client_id"] for r in items]
    return api.SyncResult(ok=True, accepted_ids=ids)


def test_chunked_oldest_first_and_capped(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 250)
    calls = []
    monkeypatch.setattr(api, "post_sessions",
                        lambda b, t, items: _ok_all(items))
    def _acts(b, t, items):
        calls.append([r["client_id"] for r in items])
        return _ok_all(items)
    monkeypatch.setattr(api, "post_activities", _acts)
    stats = sync.drain(con, {}, reason="test", notify_fn=lambda *a: False)
    assert stats["sent_sessions"] == 1 and stats["sent_activities"] == 250
    assert [len(c) for c in calls] == [100, 100, 50]
    assert calls[0][0] == "activity:1"  # oldest first
    assert store.pending_counts(con)["activities"] == 0
    con.close()


def test_partial_ack_marks_subset_and_stops(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 5)
    monkeypatch.setattr(api, "post_sessions",
                        lambda b, t, items: _ok_all(items))
    monkeypatch.setattr(
        api, "post_activities",
        lambda b, t, items: api.SyncResult(ok=True, accepted_ids=[items[0]["client_id"]]))
    stats = sync.drain(con, {}, reason="test", notify_fn=lambda *a: False)
    assert stats["sent_activities"] == 1
    assert [r[0] for r in store.pending_activities(con, 10)] == [2, 3, 4, 5]
    con.close()


def test_invalid_response_marks_nothing(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 3)
    monkeypatch.setattr(api, "post_sessions",
                        lambda b, t, items: api.SyncResult(ok=False, error="boom"))
    notes = []
    monkeypatch.setattr(sync.api, "post_sessions", lambda b, t, items: api.SyncResult(ok=False, error="boom"))
    stats = sync.drain(con, {}, reason="test", notify_fn=lambda *a: (notes.append(a), False)[1])
    assert stats["sent_sessions"] == 0
    assert store.pending_counts(con)["sessions"] == 1
    assert notes  # failure notified
    con.close()


def test_offline_queues_quietly(tmp_path):
    con = store.connect(tmp_path / "t.db")
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    store.add_activity(con, sid, "2026-01-01T00:00:05+00:00", "A", "t", 0)
    stats = sync.drain(con, {}, reason="test", notify_fn=lambda *a: (_ for _ in ()).throw(AssertionError()))
    assert stats["skipped"] is True
    con.close()


def test_sync_control_defaults_enabled_and_pauses_scheduled_drain():
    control = sync.SyncControl()
    stop = threading.Event()
    assert control.is_enabled()
    control.set_enabled(False)
    assert not control.is_enabled()
    stop.set()
    assert control.wait_for_drain(stop, 0) is False


def test_sync_control_resume_wakes_waiter_immediately():
    control = sync.SyncControl()
    stop = threading.Event()
    control.set_enabled(False)
    result = []
    waiter = threading.Thread(target=lambda: result.append(control.wait_for_drain(stop, 60)))
    waiter.start()
    control.set_enabled(True)
    waiter.join(timeout=2)
    assert result == [True]


def test_flush_deadline_and_ledger(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 10)
    monkeypatch.setattr(api, "post_sessions", lambda b, t, items: _ok_all(items))
    monkeypatch.setattr(api, "post_activities", lambda b, t, items: _ok_all(items))
    remaining = sync.flush(con, {}, timeout=30, reason="close", notify_fn=lambda *a: False)
    assert remaining == 0
    assert store.last_sync(con) is not None
    con.close()


def test_cleanup_keeps_recent_deletes_old(tmp_path):
    con = store.connect(tmp_path / "t.db")
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    old_p, new_p = str(tmp_path / "old.jpg"), str(tmp_path / "new.jpg")
    open(old_p, "w").write("x")
    open(new_p, "w").write("x")
    store.add_screenshot(con, sid, "2026-01-01T00:00:00+00:00", old_p)
    store.add_screenshot(con, sid, "2026-01-01T00:00:00+00:00", new_p)
    store.mark_uploaded(con, "screenshots", [1, 2])
    con.execute("UPDATE screenshots SET uploaded_at=? WHERE id=1", ("2000-01-01T00:00:00+00:00",))
    con.commit()
    assert cleanup_screenshots(con) == 1
    import os

    assert not os.path.exists(old_p) and os.path.exists(new_p)
    assert [r[0] for r in con.execute("SELECT id FROM screenshots").fetchall()] == [2]
    con.close()


def test_notify_once_per_day(tmp_path):
    from moon_tracker import notify

    con = store.connect(tmp_path / "t.db")
    assert notify.send(con, "sync_failed", "t", "m") is True
    assert notify.send(con, "sync_failed", "t", "m") is False  # throttled same day
    con.close()


def test_run_budget_defers_remainder(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 250)
    monkeypatch.setattr(api, "post_sessions", lambda b, t, items: _ok_all(items))
    monkeypatch.setattr(api, "post_activities", lambda b, t, items: _ok_all(items))
    stats = sync.drain(con, {}, reason="test", deadline=time.time() - 1,
                       notify_fn=lambda *a: False)
    assert stats["sent_activities"] == 0  # past deadline: nothing sent
    assert "budget exceeded" in stats["error"]
    assert store.pending_counts(con)["activities"] == 250
    last = store.last_sync(con)
    assert last is not None and "budget exceeded" in last[6]
    con.close()


def test_flush_honors_deadline(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 1000)

    def _slow(b, t, items):
        time.sleep(0.5)
        return _ok_all(items)

    monkeypatch.setattr(api, "post_sessions", lambda b, t, items: _ok_all(items))
    monkeypatch.setattr(api, "post_activities", _slow)
    t0 = time.monotonic()
    remaining = sync.flush(con, {}, timeout=1, reason="close", notify_fn=lambda *a: False)
    elapsed = time.monotonic() - t0
    assert remaining > 0  # stopped early, leftovers deferred
    assert elapsed < 8  # hard deadline honored (far under 30s close budget)
    con.close()


def test_three_failed_ticks_single_toast(tmp_path, monkeypatch):
    from moon_tracker import notify

    con = store.connect(tmp_path / "t.db")
    _seed(con, 5)
    monkeypatch.setattr(
        api, "post_sessions",
        lambda b, t, items: api.SyncResult(ok=False, error="net down"))
    monkeypatch.setattr(
        api, "post_activities",
        lambda b, t, items: api.SyncResult(ok=False, error="net down"))
    toasts = []
    monkeypatch.setattr(notify, "_send_desktop", lambda *a: (toasts.append(a), True)[1])
    for _ in range(3):
        sync.drain(con, {}, reason="tick")  # real _default_notify path, throttled 1/day
    assert len(toasts) == 1  # throttled to once per day
    assert store.pending_counts(con)["sessions"] == 1  # nothing lost
    con.close()
