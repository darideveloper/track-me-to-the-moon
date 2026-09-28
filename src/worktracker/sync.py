"""Background uploader: drains screenshot outbox with backoff. Activities piggyback."""
from __future__ import annotations

import os
import threading
import time

from . import api


def loop(con, cfg: dict, stop: threading.Event) -> None:
    backoff = 60
    while not stop.wait(backoff):
        try:
            if _drain(con, cfg):
                backoff = 60
            else:
                backoff = min(backoff * 2, 900) if cfg.get("api_base") else 60
        except Exception:
            backoff = min(backoff * 2, 900)


def _drain(con, cfg: dict) -> bool:
    from . import store

    base, token = cfg.get("api_base", ""), cfg.get("api_token", "")
    if not base:
        return True  # offline mode: nothing to do, keep queue
    rows = store.pending_screenshots(con, 20)
    if not rows:
        return True
    ok_all = True
    for sid, session_id, ts, path in rows:
        try:
            ok = api.post_screenshot(
                base, token,
                {"user_id": cfg.get("user_id", ""), "session_id": session_id, "ts": ts},
                path,
            )
        except Exception:
            ok = False
        if ok:
            store.mark_screenshot_uploaded(con, sid)
            try:
                os.remove(path)
            except OSError:
                pass
        else:
            ok_all = False
            break
    return ok_all
