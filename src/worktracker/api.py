"""Typed client for the tracker API (client-defined contract, see design.md)."""
from __future__ import annotations

from dataclasses import dataclass

import requests

TIMEOUT = 15


@dataclass
class SyncResult:
    ok: bool = False
    accepted_ids: list[str] | None = None  # None = all-or-nothing backend, ok:true, no list
    retryable: bool = True
    auth_error: bool = False
    error: str = ""
    status: int | None = None


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


def _post_json(path: str, api_base: str, token: str, items: list[dict]) -> SyncResult:
    if not api_base:
        return SyncResult(ok=False, retryable=False, error="no api_base")
    sent_ids = [str(r.get("client_id", "")) for r in items]
    try:
        r = requests.post(
            f"{api_base.rstrip('/')}{path}",
            json={"items": items},
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.Timeout:
        return SyncResult(ok=False, retryable=True, error="timeout")
    except Exception as e:
        return SyncResult(ok=False, retryable=True, error=str(e)[:200])
    return _parse_ack(r, sent_ids)


def post_sessions(api_base: str, token: str, rows: list[dict]) -> SyncResult:
    return _post_json("/v1/sessions", api_base, token, rows)


def post_activities(api_base: str, token: str, rows: list[dict]) -> SyncResult:
    return _post_json("/v1/activities", api_base, token, rows)


def post_screenshot(api_base: str, token: str, meta: dict, path: str) -> SyncResult:
    if not api_base:
        return SyncResult(ok=False, retryable=False, error="no api_base")
    sent = [str(meta.get("client_id", ""))]
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
        return SyncResult(ok=False, retryable=True, error="timeout")
    except FileNotFoundError:
        # File vanished (retention cleanup raced us): treat as accepted so the
        # row doesn't block the outbox forever.
        return SyncResult(ok=True, accepted_ids=sent)
    except Exception as e:
        return SyncResult(ok=False, retryable=True, error=str(e)[:200])
    res = _parse_ack(r, sent)
    return res
