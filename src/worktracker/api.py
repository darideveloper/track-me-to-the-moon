"""Thin client for the proprietary API. Adapt paths here when spec arrives."""
from __future__ import annotations

import requests

TIMEOUT = 15


def post_activities(api_base: str, token: str, rows: list[dict]) -> bool:
    if not api_base:
        return False
    r = requests.post(
        f"{api_base.rstrip('/')}/v1/activities",
        json={"items": rows},
        headers={"Authorization": f"Bearer {token}"} if token else {},
        timeout=TIMEOUT,
    )
    return r.ok


def post_screenshot(api_base: str, token: str, meta: dict, path: str) -> bool:
    if not api_base:
        return False
    with open(path, "rb") as f:
        r = requests.post(
            f"{api_base.rstrip('/')}/v1/screenshots",
            data=meta,
            files={"file": ("shot.jpg", f, "image/jpeg")},
            headers={"Authorization": f"Bearer {token}"} if token else {},
            timeout=TIMEOUT,
        )
    return r.ok
