"""Failure toasts, throttled to once per calendar day per kind.

Spike (2026-09-28, this venv): `desktop_notifier` and `plyer` NOT installed,
`pystray` available. So: no new hard dependency; try optional backends in
order desktop-notifier -> plyer -> pystray -> logging fallback.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

log = logging.getLogger("worktracker.notify")


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def should_notify(con, kind: str) -> bool:
    from . import store

    try:
        return store.get_setting(con, f"last_notify_{kind}") != _today()
    except Exception:
        return True


def mark_notified(con, kind: str) -> None:
    from . import store

    try:
        store.set_setting(con, f"last_notify_{kind}", _today())
    except Exception:
        pass


def _send_desktop(title: str, message: str) -> bool:
    try:
        from desktop_notifier import DesktopNotifier  # type: ignore

        DesktopNotifier().send_sync(title=title, message=message)
        return True
    except Exception:
        pass
    try:
        from plyer import notification  # type: ignore

        notification.notify(title=title, message=message, app_name="worktracker")
        return True
    except Exception:
        pass
    try:
        import pystray  # type: ignore
        from PIL import Image  # type: ignore

        icon = pystray.Icon(
            "worktracker-toast", Image.new("RGB", (64, 64), "grey"), "worktracker"
        )
        icon.notify(message, title)
        try:
            icon.stop()
        except Exception:
            pass
        return True
    except Exception:
        pass
    log.warning("sync notification (no toast backend): %s: %s", title, message)
    return False


def send(con, kind: str, title: str, message: str) -> bool:
    """Toast at most once/day per kind. Returns True if a toast was attempted."""
    if not should_notify(con, kind):
        return False
    mark_notified(con, kind)
    try:
        _send_desktop(title, message)
    except Exception:
        pass
    return True
