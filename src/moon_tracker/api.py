"""Typed client for the tracker API (client-defined contract, see design.md)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

TIMEOUT = 15
REQ_PREVIEW_LIMIT = 2048
RES_PREVIEW_LIMIT = 1024


@dataclass
class SyncResult:
    ok: bool = False
    accepted_ids: list[str] | None = None  # None = all-or-nothing backend, ok:true, no list
    retryable: bool = True
    auth_error: bool = False
    error: str = ""
    status: int | None = None


@dataclass
class ApiEvent:
    """One HTTP call for the debug log. Token is never stored here."""

    ts: str = ""
    method: str = ""
    path: str = ""
    item_count: int = 0
    status: int | None = None
    ok: bool = False
    accepted: int | None = None
    error: str = ""
    req_preview: str = ""
    res_preview: str = ""
    auth: str = "missing"  # "present" | "missing"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"…[truncated {len(text) - limit} more chars]"


def _preview_items(items: list[dict] | dict, token: str = "", limit: int = REQ_PREVIEW_LIMIT) -> str:
    try:
        s = json.dumps(items, default=str)
    except Exception:
        s = str(items)[:limit]
    if token and token in s:
        s = s.replace(token, "***REDACTED***")
    return _truncate(s, limit)


def _preview_body(body, limit: int = RES_PREVIEW_LIMIT) -> str:
    try:
        s = body if isinstance(body, str) else json.dumps(body, default=str)
    except Exception:
        s = str(body)
    return _truncate(s, limit)


def _emit_safe(emit, event: ApiEvent) -> None:
    try:
        if emit is not None:
            emit(event)
    except Exception:
        pass


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _parse_ack(resp: requests.Response, sent_ids: list[str]) -> SyncResult:
    status = resp.status_code
    if 200 <= status < 300:
        try:
            body = resp.json()
        except Exception:
            body = None
        if isinstance(body, dict) and body.get("ok") is True:
            acc = body.get("accepted")
            if acc is None:
                return SyncResult(ok=True, accepted_ids=None, status=status)
            acc_list = [str(x) for x in acc] if isinstance(acc, list) else []
            return SyncResult(ok=True, accepted_ids=acc_list, status=status)
        if body is None and status == 200:
            # Tolerate empty-body 200 as full ack (very old stub backends).
            return SyncResult(ok=True, accepted_ids=None, status=status)
        return SyncResult(ok=False, retryable=True, error=f"invalid ack (http {status})", status=status)
    if status == 429 or 500 <= status < 600:
        return SyncResult(ok=False, retryable=True, error=f"http {status}", status=status)
    if status in (401, 403):
        return SyncResult(ok=False, retryable=False, auth_error=True, error=f"http {status}", status=status)
    return SyncResult(ok=False, retryable=False, error=f"http {status}", status=status)


def _post_json(path: str, api_base: str, token: str, items: list[dict],
               emit=None) -> SyncResult:
    auth = "present" if token else "missing"
    req_preview = _preview_items(items, token)
    if not api_base:
        res = SyncResult(ok=False, retryable=False, error="no api_base")
        _emit_safe(emit, ApiEvent(ts=_now(), method="POST", path=path,
                                 item_count=len(items), status=None, ok=False,
                                 error=res.error, req_preview=req_preview,
                                 res_preview="", auth=auth))
        return res
    sent_ids = [str(r.get("client_id", "")) for r in items]
    try:
        r = requests.post(
            f"{api_base.rstrip('/')}{path}",
            json={"items": items},
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.Timeout:
        res = SyncResult(ok=False, retryable=True, error="timeout")
        _emit_safe(emit, ApiEvent(ts=_now(), method="POST", path=path,
                                 item_count=len(items), status=None, ok=False,
                                 error=res.error, req_preview=req_preview,
                                 res_preview="", auth=auth))
        return res
    except Exception as e:
        res = SyncResult(ok=False, retryable=True, error=str(e)[:200])
        _emit_safe(emit, ApiEvent(ts=_now(), method="POST", path=path,
                                 item_count=len(items), status=None, ok=False,
                                 error=res.error, req_preview=req_preview,
                                 res_preview="", auth=auth))
        return res
    res = _parse_ack(r, sent_ids)
    try:
        raw = getattr(r, "text", "")
    except Exception:
        raw = ""
    accepted = None if res.accepted_ids is None else len(res.accepted_ids)
    _emit_safe(emit, ApiEvent(ts=_now(), method="POST", path=path,
                             item_count=len(items), status=res.status, ok=res.ok,
                             accepted=accepted, error=res.error,
                             req_preview=req_preview,
                             res_preview=_preview_body(raw), auth=auth))
    return res


def post_sessions(api_base: str, token: str, rows: list[dict], emit=None) -> SyncResult:
    return _post_json("/v1/sessions", api_base, token, rows, emit=emit)


def post_activities(api_base: str, token: str, rows: list[dict], emit=None) -> SyncResult:
    return _post_json("/v1/activities", api_base, token, rows, emit=emit)


def post_screenshot(api_base: str, token: str, meta: dict, path: str, emit=None) -> SyncResult:
    auth = "present" if token else "missing"
    sent = [str(meta.get("client_id", ""))]
    try:
        import os as _os

        size = _os.path.getsize(path)
    except Exception:
        size = -1
    req_preview = _preview_items({"meta": meta, "file_bytes": size}, token)
    if not api_base:
        res = SyncResult(ok=False, retryable=False, error="no api_base")
        _emit_safe(emit, ApiEvent(ts=_now(), method="POST", path="/v1/screenshots",
                                 item_count=1, status=None, ok=False,
                                 error=res.error, req_preview=req_preview,
                                 res_preview="", auth=auth))
        return res
    try:
        with open(path, "rb") as f:
            r = requests.post(
                f"{api_base.rstrip('/')}/v1/screenshots",
                data=meta,
                files={"file": ("shot.jpg", f, "image/jpeg")},
                headers=_headers(token),
                timeout=TIMEOUT,
            )
    except requests.Timeout:
        res = SyncResult(ok=False, retryable=True, error="timeout")
        _emit_safe(emit, ApiEvent(ts=_now(), method="POST", path="/v1/screenshots",
                                 item_count=1, status=None, ok=False,
                                 error=res.error, req_preview=req_preview,
                                 res_preview="", auth=auth))
        return res
    except FileNotFoundError:
        # File vanished (retention cleanup raced us): treat as accepted so the
        # row doesn't block the outbox forever.
        res = SyncResult(ok=True, accepted_ids=sent)
        _emit_safe(emit, ApiEvent(ts=_now(), method="POST", path="/v1/screenshots",
                                 item_count=1, status=None, ok=True,
                                 accepted=1, error="file vanished, treated as sent",
                                 req_preview=req_preview, res_preview="",
                                 auth=auth))
        return res
    except Exception as e:
        res = SyncResult(ok=False, retryable=True, error=str(e)[:200])
        _emit_safe(emit, ApiEvent(ts=_now(), method="POST", path="/v1/screenshots",
                                 item_count=1, status=None, ok=False,
                                 error=res.error, req_preview=req_preview,
                                 res_preview="", auth=auth))
        return res
    res = _parse_ack(r, sent)
    try:
        raw = getattr(r, "text", "")
    except Exception:
        raw = ""
    accepted = None if res.accepted_ids is None else len(res.accepted_ids)
    _emit_safe(emit, ApiEvent(ts=_now(), method="POST", path="/v1/screenshots",
                             item_count=1, status=res.status, ok=res.ok,
                             accepted=accepted, error=res.error,
                             req_preview=req_preview,
                             res_preview=_preview_body(raw), auth=auth))
    return res


def test_connection(api_base: str, token: str, emit=None) -> SyncResult:
    """Probe reachability without touching the outbox. GET /health, then empty probe."""
    auth = "present" if token else "missing"
    base = (api_base or "").strip()
    if not base:
        res = SyncResult(ok=False, retryable=False, error="no api_base")
        _emit_safe(emit, ApiEvent(ts=_now(), method="GET", path="/health",
                                 item_count=0, status=None, ok=False,
                                 error=res.error, req_preview="",
                                 res_preview="", auth=auth))
        return res
    try:
        r = requests.get(f"{base.rstrip('/')}/health", headers=_headers(token),
                         timeout=TIMEOUT)
        status = r.status_code
        try:
            raw = getattr(r, "text", "")
        except Exception:
            raw = ""
        ok = 200 <= status < 300
        res = SyncResult(ok=ok, accepted_ids=[], status=status,
                         retryable=not ok and (status == 429 or 500 <= status < 600),
                         auth_error=status in (401, 403),
                         error="" if ok else f"http {status}")
        _emit_safe(emit, ApiEvent(ts=_now(), method="GET", path="/health",
                                 item_count=0, status=status, ok=ok,
                                 accepted=0 if ok else None, error=res.error,
                                 req_preview="", res_preview=_preview_body(raw),
                                 auth=auth))
        if ok or status not in (404, 405):
            return res
    except requests.Timeout:
        res = SyncResult(ok=False, retryable=True, error="timeout")
        _emit_safe(emit, ApiEvent(ts=_now(), method="GET", path="/health",
                                 item_count=0, status=None, ok=False,
                                 error=res.error, req_preview="",
                                 res_preview="", auth=auth))
    except Exception as e:
        _emit_safe(emit, ApiEvent(ts=_now(), method="GET", path="/health",
                                 item_count=0, status=None, ok=False,
                                 error=str(e)[:200], req_preview="",
                                 res_preview="", auth=auth))
    return _post_json("/v1/sessions", base, token, [], emit=emit)
