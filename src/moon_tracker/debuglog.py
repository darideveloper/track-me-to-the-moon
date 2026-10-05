"""Session-only API call ring for the debug panel. No DB, no token storage."""
from __future__ import annotations

import threading
from collections import deque

MAX_EVENTS = 200

_LOCK = threading.Lock()
_BUF: deque = deque(maxlen=MAX_EVENTS)


def append(event) -> None:
    try:
        with _LOCK:
            _BUF.append(event)
    except Exception:
        pass


def recent(n: int = MAX_EVENTS) -> list:
    with _LOCK:
        items = list(_BUF)[-max(0, n):]
    return items[::-1]  # newest first


def clear() -> None:
    with _LOCK:
        _BUF.clear()


def __len__() -> int:  # pragma: no cover - convenience only
    with _LOCK:
        return len(_BUF)


def compact(event) -> str:
    """One-line summary: `HH:MM:SS POST /v1/activities → 12 items ← 200 accepted:12`."""
    try:
        ts = str(getattr(event, "ts", ""))[11:19] or str(getattr(event, "ts", ""))
        method = getattr(event, "method", "")
        path = getattr(event, "path", "")
        n = getattr(event, "item_count", 0)
        status = getattr(event, "status", None)
        ok = getattr(event, "ok", False)
        accepted = getattr(event, "accepted", None)
        error = getattr(event, "error", "") or ""
        head = f"{ts} {method} {path} → {n} items".strip()
        if status is None:
            tail = f"← {error or 'no response'}"
        elif ok:
            tail = f"← {status} accepted:{accepted if accepted is not None else 'all'}"
        else:
            tail = f"← {status} {error}" if error != f"http {status}" else f"← {error}"
        return f"{head} {tail}".strip()
    except Exception:
        return "api event"


def format_bundle(version: str, pending: dict, last_sync, events: list,
                  data_dir=None) -> str:
    """Paste-ready debug report. Never includes the API token (never stored)."""
    lines = [f"moon-tracker {version or 'unknown'}"]
    if data_dir is not None:
        lines.append(f"data dir: {data_dir}")
    try:
        total = int(pending.get("sessions", 0) + pending.get("activities", 0)
                    + pending.get("screenshots", 0))
        lines.append(f"pending: {total} "
                     f"(sessions={pending.get('sessions', 0)} "
                     f"activities={pending.get('activities', 0)} "
                     f"screenshots={pending.get('screenshots', 0)})")
    except Exception:
        lines.append("pending: ?")
    try:
        if last_sync:
            lines.append(f"last sync: {last_sync[0]} reason={last_sync[2]} "
                         f"sent s/a/sh={last_sync[3]}/{last_sync[4]}/{last_sync[5]} "
                         f"error={last_sync[6] or '—'}")
        else:
            lines.append("last sync: none yet")
    except Exception:
        lines.append("last sync: ?")
    lines.append(f"api calls (newest {len(events)}):")
    for e in events[:20]:
        lines.append(f"- {compact(e)}")
        req = str(getattr(e, "req_preview", "") or "")[:500]
        res = str(getattr(e, "res_preview", "") or "")[:500]
        if req:
            lines.append(f"  req: {req}")
        if res:
            lines.append(f"  res: {res}")
    return "\n".join(lines)
