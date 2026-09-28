"""Poll active window: returns (app, title). Title-only, no URLs."""
from __future__ import annotations


def poll() -> tuple[str, str]:
    try:
        import pywinctl as pwc

        title = (pwc.getActiveWindowTitle() or "").strip()
        app = ""
        try:
            w = pwc.getActiveWindow()
            if w is not None:
                app = (w.getAppName() or "").strip()
        except Exception:
            pass
        if not app:
            app = _app_from_psutil()
        return app or "unknown", title or "(no title)"
    except Exception:
        return "unknown", "(unavailable)"


def _app_from_psutil() -> str:
    try:
        import psutil

        # ponytail: cheapest heuristic — foreground guess not reliable cross-platform,
        # so return empty and let title carry the signal.
        return ""
    except Exception:
        return ""
