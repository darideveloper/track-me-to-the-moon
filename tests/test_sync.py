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


def test_loop_paused_no_drain_resume_one_drain(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 5)
    monkeypatch.setattr(api, "post_sessions", lambda b, t, items: _ok_all(items))
    monkeypatch.setattr(api, "post_activities", lambda b, t, items: _ok_all(items))
    control = sync.SyncControl()
    control.set_enabled(False)
    calls = []
    real_drain = sync.drain
    stop = threading.Event()

    def counting(*a, **k):
        calls.append(1)
        try:
            return real_drain(*a, **k)
        finally:
            stop.set()

    monkeypatch.setattr(sync, "drain", counting)
    t = threading.Thread(target=sync.loop,
                         args=(con, {"sync_interval_sec": 3600}),
                         kwargs={"stop": stop, "control": control}, daemon=True)
    t.start()
    time.sleep(0.5)
    assert calls == []  # scheduled ticks issue nothing while paused
    control.set_enabled(True)
    t.join(timeout=5)
    assert len(calls) == 1  # resume drains exactly once, immediately
    assert store.pending_counts(con)["activities"] == 0
    con.close()


def test_pause_mid_run_stops_new_posts(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 300)
    monkeypatch.setattr(api, "post_sessions", lambda b, t, items: _ok_all(items))
    posts = []

    def _slow(b, t, items):
        posts.append(len(items))
        time.sleep(0.3)
        return _ok_all(items)

    monkeypatch.setattr(api, "post_activities", _slow)
    control = sync.SyncControl()
    done = threading.Event()

    def run():
        sync.drain(con, {}, reason="tick", notify_fn=lambda *a: False, control=control)
        done.set()

    th = threading.Thread(target=run)
    th.start()
    time.sleep(0.15)
    control.set_enabled(False)  # pause lands mid first chunk
    assert done.wait(timeout=10)
    th.join(timeout=5)
    assert posts == [100]  # in-flight chunk finishes, nothing new starts
    assert store.pending_counts(con)["activities"] == 200
    last = store.last_sync(con)
    assert last is not None and "paused" in (last[6] or "")
    con.close()


def test_flush_skipped_while_paused(tmp_path, monkeypatch):
    con = store.connect(tmp_path / "t.db")
    _seed(con, 5)
    control = sync.SyncControl()
    control.set_enabled(False)

    def _boom(*a, **k):
        raise AssertionError("drain must not run while paused")

    monkeypatch.setattr(sync, "drain", _boom)
    assert sync.flush(con, {}, timeout=5, reason="close", control=control) == 6
    assert sync.kept_while_paused(con, control) == 6  # 1 session + 5 activities
    assert sync.kept_while_paused(con, sync.SyncControl()) is None
    con.close()


def test_close_flush_reports_kept_while_paused(tmp_path, monkeypatch, capsys):
    from moon_tracker import app as tray_app

    con = store.connect(tmp_path / "t.db")
    _seed(con, 5)
    control = sync.SyncControl()
    control.set_enabled(False)

    def _boom(*a, **k):
        raise AssertionError("sync.flush must not run while paused")

    monkeypatch.setattr(tray_app.sync, "flush", _boom)
    assert tray_app._close_flush(con, {}, control=control) == 6
    assert "kept" in capsys.readouterr().out
    con.close()


def test_retention_cleanup_runs_while_paused(tmp_path):
    con = store.connect(tmp_path / "t.db")
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    old_p, new_p, unsent_p = (str(tmp_path / "old.jpg"), str(tmp_path / "new.jpg"),
                              str(tmp_path / "unsent.jpg"))
    for p in (old_p, new_p, unsent_p):
        open(p, "w").write("x")
    store.add_screenshot(con, sid, "2026-01-01T00:00:00+00:00", old_p)
    store.add_screenshot(con, sid, "2026-01-01T00:00:00+00:00", new_p)
    store.add_screenshot(con, sid, "2026-01-01T00:00:00+00:00", unsent_p)
    store.mark_uploaded(con, "screenshots", [1, 2])
    con.execute("UPDATE screenshots SET uploaded_at=? WHERE id=1", ("2000-01-01T00:00:00+00:00",))
    con.commit()
    control = sync.SyncControl()
    control.set_enabled(False)
    sync.run_retention_cleanup_if_due(con)  # no network involved by construction
    import os

    assert not os.path.exists(old_p) and os.path.exists(new_p)
    assert os.path.exists(unsent_p)  # unsent rows/files never auto-deleted
    assert sorted(r[0] for r in con.execute("SELECT id FROM screenshots").fetchall()) == [2, 3]
    con.close()


def test_tray_state_carries_shared_control():
    from moon_tracker import app as tray_app

    state = tray_app._new_tray_state()
    assert isinstance(state["sync_control"], sync.SyncControl)
    assert state["sync_control"].is_enabled()
    assert tray_app._sync_menu_label(state) == "Pause sync"
    state["sync_control"].set_enabled(False)
    assert tray_app._sync_menu_label(state) == "Resume sync"


def test_background_threads_use_tray_control(tmp_path, monkeypatch):
    from moon_tracker import app as tray_app

    con = store.connect(tmp_path / "t.db")
    _seed(con, 3)
    state = tray_app._new_tray_state()
    state["sync_control"].set_enabled(False)

    def _boom(*a, **k):
        raise AssertionError("drain must not run while paused")

    monkeypatch.setattr(tray_app.sync, "drain", _boom)
    stop = threading.Event()
    threads = tray_app.start_background_threads(
        con, {"poll_interval_sec": 3600, "sync_interval_sec": 3600}, state, stop, tmp_path)
    time.sleep(0.5)
    stop.set()
    for t in threads:
        t.join(timeout=3)
    assert store.pending_counts(con)["activities"] == 3
    con.close()


def test_paused_label():
    from moon_tracker import brand

    assert "paused" in brand.paused_label(3) and "3" in brand.paused_label(3)
    assert "paused" in brand.paused_label(0)
    assert "unauthorized" not in brand.paused_label(3)  # distinct from auth hint
