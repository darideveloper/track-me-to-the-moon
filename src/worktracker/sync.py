"""Background sync: 10-min outbox drain with ack-only marking + close flush."""
from __future__ import annotations

import os
import random
import threading
import time
from datetime import datetime, timedelta, timezone

from . import api

SYNC_INTERVAL_SEC = 600
JITTER_SEC = 30
CHUNK_JSON = 100
MAX_CHUNKS_PER_RUN = 10
MAX_RUN_SEC = 120
SCREENSHOT_TTL_DAYS = 7


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deadline_exceeded(deadline: float | None) -> bool:
    return deadline is not None and time.time() >= deadline


def _mark_chunk(con, table: str, sent_ids: list[int], res: api.SyncResult) -> tuple[int, bool]:
    """Apply an ack to the outbox. Returns (marked_count, should_continue)."""
    from . import store

    if not res.ok:
        store.note_error(con, table, sent_ids, res.error or "sync failed")
        return 0, False
    if res.accepted_ids is None:  # all-or-nothing backend fallback
        store.mark_uploaded(con, table, sent_ids)
        return len(sent_ids), True
    accepted = {a.split(":", 1)[1] for a in res.accepted_ids if ":" in a}
    hit = [i for i in sent_ids if str(i) in accepted]
    if hit:
        store.mark_uploaded(con, table, hit)
    rest = [i for i in sent_ids if str(i) not in accepted]
    if rest:
        store.note_error(con, table, rest, "not accepted")
        return len(hit), False  # head-of-line: retry remainder next tick
    return len(hit), True


def _drain_json(
    con,
    table: str,
    fetch,
    build_items,
    post,
    stats_key: str,
    stats: dict,
    deadline: float | None,
    chunks_used: list[int],
) -> bool:
    """Drain one JSON table in chunks. Returns False to stop the whole run."""
    while chunks_used[0] < MAX_CHUNKS_PER_RUN and not _deadline_exceeded(deadline):
        rows = fetch(con, CHUNK_JSON)
        if not rows:
            return True
        ids = [r[0] for r in rows]
        items = build_items(rows)
        res = post(items)
        marked, cont = _mark_chunk(con, table, ids, res)
        stats[stats_key] += marked
        chunks_used[0] += 1
        if res.auth_error:
            stats["auth_error"] = True
            stats["error"] = res.error
            return False
        if not res.ok:
            stats["error"] = res.error
            stats["failed"] = True
            return False
        if not cont:
            stats["error"] = "partial ack"
            stats["failed"] = True
            return False
    return not _deadline_exceeded(deadline)


def drain(con, cfg: dict, reason: str = "tick", deadline: float | None = None,
          notify_fn=None) -> dict:
    """One bounded sync run. Never raises; always writes a ledger row."""
    from . import store

    t0 = time.time()
    started = _now()
    stats = {"sent_sessions": 0, "sent_activities": 0, "sent_screenshots": 0,
             "error": "", "failed": False, "auth_error": False, "skipped": False}
    try:
        s = store.get_settings_dict(con)
        base, token, user = s.get("api_base", ""), s.get("api_token", ""), s.get("user_id", "")
        if not base:
            stats["skipped"] = True
            return stats
        chunks = [0]

        ok = _drain_json(
            con, "sessions", store.pending_sessions,
            lambda rows: [
                {"client_id": f"session:{r[0]}", "session_id": r[0],
                 "started_at": r[1], "ended_at": r[2], "user_id": user}
                for r in rows
            ],
            lambda items: api.post_sessions(base, token, items),
            "sent_sessions", stats, deadline, chunks,
        )
        if ok:
            ok = _drain_json(
                con, "activities", store.pending_activities,
                lambda rows: [
                    {"client_id": f"activity:{r[0]}", "session_id": r[1], "ts": r[2],
                     "app": r[3], "title": r[4], "idle": r[5], "user_id": user}
                    for r in rows
                ],
                lambda items: api.post_activities(base, token, items),
                "sent_activities", stats, deadline, chunks,
            )
        if ok:
            while chunks[0] < MAX_CHUNKS_PER_RUN and not _deadline_exceeded(deadline):
                if time.time() - t0 >= MAX_RUN_SEC:
                    break
                rows = store.pending_screenshots(con, 1)
                if not rows:
                    break
                sid, session_id, ts, path = rows[0]
                meta = {"client_id": f"screenshot:{sid}", "session_id": session_id,
                        "ts": ts, "user_id": user}
                res = api.post_screenshot(base, token, meta, path)
                if res.ok:
                    store.mark_uploaded(con, "screenshots", [sid])
                    stats["sent_screenshots"] += 1
                    chunks[0] += 1
                    continue
                store.note_error(con, "screenshots", [sid], res.error or "sync failed")
                stats["error"] = res.error
                stats["failed"] = True
                if res.auth_error:
                    stats["auth_error"] = True
                break
        if _deadline_exceeded(deadline) or time.time() - t0 >= MAX_RUN_SEC:
            stats["error"] = stats["error"] or "run budget exceeded, remainder deferred"
        _maybe_cleanup(con)
    except Exception as e:  # never break the loop thread on unexpected errors
        stats["error"] = str(e)[:200]
        stats["failed"] = True
    finally:
        try:
            store.log_sync_run(
                con, started, reason,
                stats["sent_sessions"], stats["sent_activities"], stats["sent_screenshots"],
                "" if stats["skipped"] else stats["error"],
            )
        except Exception:
            pass
        if stats.get("failed") and not stats.get("skipped"):
            try:
                (notify_fn or _default_notify)(
                    con, "sync_failed", "worktracker sync failed",
                    stats["error"] or "upload failed; will retry in 10 minutes")
            except Exception:
                pass
    return stats


def _default_notify(con, kind: str, title: str, message: str) -> bool:
    from . import notify

    return notify.send(con, kind, title, message)


def _maybe_cleanup(con) -> None:
    """Delete acked screenshot files+rows older than TTL (daily gate)."""
    from . import store

    try:
        if store.get_setting(con, "last_notify_cleanup") == datetime.now(timezone.utc).date().isoformat():
            return
    except Exception:
        pass
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=SCREENSHOT_TTL_DAYS)).isoformat()
        for sid, path in store.uploaded_screenshots_before(con, cutoff, 200):
            try:
                os.remove(path)
            except OSError:
                pass
            try:
                store.delete_screenshot_row(con, sid)
            except Exception:
                pass
        try:
            store.set_setting(con, "last_notify_cleanup",
                              datetime.now(timezone.utc).date().isoformat())
        except Exception:
            pass
    except Exception:
        pass


def cleanup_screenshots(con, days: int = SCREENSHOT_TTL_DAYS) -> int:
    """Testable retention cleanup. Returns rows removed. Never touches unsent rows."""
    import os as _os

    from . import store

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    removed = 0
    for sid, path in store.uploaded_screenshots_before(con, cutoff, 1000):
        try:
            _os.remove(path)
        except OSError:
            pass
        store.delete_screenshot_row(con, sid)
        removed += 1
    return removed


def flush(con, cfg: dict, timeout: float = 30, reason: str = "close", notify_fn=None) -> int:
    """Blocking drain with hard deadline. Returns remaining pending count."""
    from . import store

    drain(con, cfg, reason=reason, deadline=time.time() + timeout, notify_fn=notify_fn)
    try:
        c = store.pending_counts(con)
        return c.get("sessions", 0) + c.get("activities", 0) + c.get("screenshots", 0)
    except Exception:
        return -1


def loop(con, cfg: dict, stop: threading.Event, notify_fn=None) -> None:
    interval = cfg.get("sync_interval_sec", SYNC_INTERVAL_SEC)
    while not stop.wait(float(interval) + random.uniform(-JITTER_SEC, JITTER_SEC)):
        try:
            drain(con, cfg, reason="tick", notify_fn=notify_fn)
        except Exception:
            pass


# Back-compat for the pre-outbox uploader (tests/callers): drain fully, return ok.
def _drain(con, cfg: dict) -> bool:
    stats = drain(con, cfg, reason="legacy")
    return not stats.get("failed", False)
