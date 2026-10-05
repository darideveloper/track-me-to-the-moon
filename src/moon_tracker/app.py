"""Tray app: Start/Stop + collector/screenshot/uploader threads."""
from __future__ import annotations

import argparse
import random
import threading
import time
from datetime import datetime, timezone

from . import brand, collect, config, idle, shots, store, sync


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_background_threads(con, cfg: dict, state: dict, stop: threading.Event,
                             data_dir=None) -> list:
    """Collector + uploader daemon threads shared by tray and Flet frontends."""
    from pathlib import Path

    ddir = Path(data_dir) if data_dir is not None else config.data_dir()
    watcher = idle.IdleWatcher()

    def workers():
        last_shot = 0.0
        while not stop.wait(cfg.get("poll_interval_sec", 360)):
            if not state["running"]:
                continue
            is_idle = watcher.is_idle(cfg.get("idle_after_sec", 180))
            app, title = collect.poll()
            store.add_activity(con, state["sid"], _now(), app, title, int(is_idle))
            iv = cfg.get("screenshot_interval_sec", 900)
            if not is_idle and time.time() - last_shot >= iv + random.uniform(0, 120):
                p = shots.take(ddir)
                if p:
                    store.add_screenshot(con, state["sid"], _now(), str(p))
                last_shot = time.time()

    threads = [
        threading.Thread(target=workers, daemon=True),
        threading.Thread(target=sync.loop, args=(con, cfg, stop), daemon=True),
    ]
    for t in threads:
        t.start()
    return threads


def _pending_total(con) -> int:
    try:
        c = store.pending_counts(con)
        return c.get("sessions", 0) + c.get("activities", 0) + c.get("screenshots", 0)
    except Exception:
        return -1


def _tray_title(con, stopped: bool = True, data_dir=None) -> str:
    """Tray title with pending count + last-sync status (reads ledger, no thread)."""
    suffix = brand.dev_suffix(data_dir)
    try:
        total = brand.pending_total(store.pending_counts(con))
        last = store.last_sync(con)
        synced = bool(last and not last[6]) and total == 0
        return brand.tray_title(stopped, total, synced, suffix=suffix)
    except Exception:
        pass
    return brand.tray_title(stopped, 0, False, suffix=suffix)


def _close_flush(con, cfg: dict, timeout: float = 30) -> int:
    """Blocking close flush with console message. Returns remaining pending."""
    try:
        total = _pending_total(con)
        if total > 0:
            print(f"Syncing… {total} items left (up to {int(timeout)}s)")
        remaining = sync.flush(con, cfg, timeout=timeout, reason="close")
        if remaining > 0:
            print(f"Sync incomplete: {remaining} items remain, will retry next start")
        elif remaining == 0:
            print("Sync complete")
        return remaining
    except Exception as e:
        print(f"Sync failed: {e}")
        return -1


def _icon(running: bool):
    """Moon-asset tray icon (gold ring when recording), legacy dot fallback."""
    try:
        from PIL import Image, ImageDraw

        p = brand.asset_path()
        if p.exists():
            img = Image.open(p).convert("RGBA").resize((64, 64))
            if running:
                d = ImageDraw.Draw(img)
                d.ellipse([2, 2, 62, 62], outline="#7DD3FC", width=4)
            return img
    except Exception:
        pass
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (64, 64), "green" if running else "grey")
    d = ImageDraw.Draw(img)
    d.ellipse([16, 16, 48, 48], fill="white" if running else "black")
    return img


def run_tray(data_dir=None) -> None:
    import logging
    import signal

    import pystray

    # ponytail: pystray xorg _mainloop has bare `except:` that logs
    # KeyboardInterrupt from Xlib select() as "An error occurred in the
    # main loop". Silence that logger; we shut down cleanly below.
    logging.getLogger("pystray").setLevel(logging.CRITICAL)

    ddir = config.data_dir(data_dir)
    print(f"data dir: {ddir}")
    cfg = config.load()
    con = store.connect(ddir / "tracker.db")
    state = {"running": False, "sid": None}
    stop = threading.Event()
    start_background_threads(con, cfg, state, stop, ddir)

    def start(icon, _):
        if not state["running"]:
            state["sid"] = store.start_session(con, _now())
            state["running"] = True
            icon.icon = _icon(True)
            icon.title = _tray_title(con, stopped=False, data_dir=ddir)

    def stop_tracking(icon=None, _=None):
        if state["running"]:
            try:
                store.end_session(con, state["sid"], _now())
            except Exception:
                pass
            state["running"] = False
            if icon is not None:
                try:
                    icon.icon = _icon(False)
                    icon.title = _tray_title(con, stopped=True, data_dir=ddir)
                except Exception:
                    pass

    def on_quit(icon, _):
        stop_tracking(icon, _)
        stop.set()
        _close_flush(con, cfg)
        try:
            icon.stop()
        except Exception:
            pass

    menu = pystray.Menu(
        pystray.MenuItem("Launch", start),
        pystray.MenuItem("Land", stop_tracking),
        pystray.MenuItem("Quit", on_quit),
    )
    tray = pystray.Icon(brand.DISPLAY_NAME, _icon(False),
                        _tray_title(con, stopped=True, data_dir=ddir), menu)

    def _quit(signum=None, frame=None):  # Ctrl+C / kill: break Xlib select, exit quietly
        stop_tracking()
        stop.set()
        _close_flush(con, cfg)
        try:
            tray.stop()
        except Exception:
            pass

    try:
        signal.signal(signal.SIGINT, _quit)
        signal.signal(signal.SIGTERM, _quit)
    except Exception:
        pass
    try:
        tray.run()
    except KeyboardInterrupt:
        pass  # backends that re-raise instead of swallowing
    finally:
        stop_tracking()
        stop.set()
        _close_flush(con, cfg)
        try:
            con.close()
        except Exception:
            pass


def main() -> None:
    ap = argparse.ArgumentParser(prog="moon-tracker")
    ap.add_argument("--once", action="store_true", help="print one poll and exit")
    ap.add_argument("--shot", action="store_true", help="take one screenshot and exit")
    ap.add_argument("--version", action="store_true", help="print version and exit")
    ap.add_argument("--data-dir", default=None,
                    help="isolated data dir for tracker.db + shots "
                         f"(or {config.DATA_DIR_ENV} env); default is the shared OS dir")
    a = ap.parse_args()
    if a.version:
        from . import version as _version

        print(_version.get_version())
        return
    ddir = config.data_dir(a.data_dir)
    print(f"data dir: {ddir}")
    if a.once:
        print(collect.poll())
    elif a.shot:
        print(shots.take(ddir))
    else:
        from . import ui

        ui.run(ddir)


if __name__ == "__main__":
    main()
