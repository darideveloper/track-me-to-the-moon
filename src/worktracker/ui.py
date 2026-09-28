"""Flet desktop UI: live timer, Start/Stop, recent sessions."""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone

import flet as ft

from . import config, store
from .app import _now, start_background_threads


def format_hms(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_duration(total_seconds: float) -> str:
    s = max(0, int(total_seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m"
    return f"{sec}s"


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def format_session_row(started_at: str, ended_at: str | None) -> tuple[str, str]:
    """Return (title, subtitle) for a history row. Local times, open end as now."""
    now = datetime.now(timezone.utc)
    start = _parse(started_at)
    end = _parse(ended_at) if ended_at else now
    s_local = start.astimezone().strftime("%H:%M")
    e_local = end.astimezone().strftime("%H:%M") if ended_at else "now"
    day = start.astimezone().strftime("%Y-%m-%d")
    title = f"{s_local} → {e_local}"
    subtitle = f"{day} · {format_duration((end - start).total_seconds())}"
    return title, subtitle


def _snack(page, message: str) -> None:
    """Best-effort SnackBar (window may already be closing)."""
    try:
        import flet as ft

        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()
    except Exception:
        pass


def main(page: ft.Page) -> None:
    cfg = config.load()
    con = store.connect(config.data_dir() / "tracker.db")
    state = {"running": False, "sid": None, "started_at": None}
    stop = threading.Event()
    start_background_threads(con, cfg, state, stop)

    page.title = "worktracker"
    if page.window is not None:
        page.window.width = 320
        page.window.height = 450
        page.window.resizable = True

    timer_label = ft.Text("00:00:00", size=40, weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER)
    status_dot = ft.Container(width=12, height=12, border_radius=6, bgcolor=ft.Colors.GREY)
    status_text = ft.Text("Stopped")
    sync_text = ft.Text("", size=11, color=ft.Colors.GREY)
    start_btn = ft.FilledButton("Start")
    stop_btn = ft.OutlinedButton("Stop", disabled=True)
    history = ft.ListView(expand=True, spacing=4)
    settings_hint = ft.Text("Settings incomplete — open ⚙ to finish setup.",
                            size=12, visible=False, color=ft.Colors.AMBER)
    gear_btn = ft.IconButton(icon=ft.Icons.SETTINGS, tooltip="Settings")

    def current_settings() -> dict:
        return store.get_settings_dict(con)

    def refresh_hint() -> None:
        settings_hint.visible = bool(store.validate_settings(current_settings()))

    def refresh_sync_status() -> None:
        """Pending count + last-sync status (reads ledger, no extra thread)."""
        try:
            c = store.pending_counts(con)
            total = c.get("sessions", 0) + c.get("activities", 0) + c.get("screenshots", 0)
            if total > 0:
                sync_text.value = f"↻ {total} pending"
                return
            last = store.last_sync(con)
            if last is None:
                sync_text.value = ""
            elif last[6]:
                sync_text.value = f"⚠ last sync failed: {last[6][:60]}"
            else:
                sync_text.value = "✓ synced"
        except Exception:
            sync_text.value = ""

    base_field = ft.TextField(label="API base URL", hint_text="https://api.example.com",
                              dense=True)
    user_field = ft.TextField(label="Employee ID", dense=True)
    token_field = ft.TextField(label="API token", password=True,
                               can_reveal_password=False, dense=True)
    token_change_btn = ft.OutlinedButton("Change")
    save_btn = ft.FilledButton("Save")
    back_btn = ft.TextButton("‹ Back")
    settings_msg = ft.Text("", size=12)
    token_state = {"editing": True}

    def refresh_settings() -> None:
        s = current_settings()
        base_field.value = s["api_base"]
        base_field.error_text = None
        user_field.value = s["user_id"]
        user_field.error_text = None
        token_field.error_text = None
        if s["api_token"]:
            token_state["editing"] = False
            token_field.value = "•" * 8
            token_field.disabled = True
            token_change_btn.visible = True
        else:
            token_state["editing"] = True
            token_field.value = ""
            token_field.disabled = False
            token_change_btn.visible = False
        settings_msg.value = ""

    def show_settings(_=None) -> None:
        refresh_settings()
        home_view.visible = False
        settings_view.visible = True
        page.update()

    def show_home(_=None) -> None:
        settings_view.visible = False
        home_view.visible = True
        refresh_hint()
        page.update()

    def on_token_change(_=None) -> None:
        token_state["editing"] = True
        token_field.value = ""
        token_field.disabled = False
        token_field.error_text = None
        token_change_btn.visible = False
        page.update()

    def on_save(_=None) -> None:
        base = (base_field.value or "").strip()
        user = (user_field.value or "").strip()
        token = ((token_field.value or "").strip() if token_state["editing"]
                 else store.get_setting(con, "api_token"))
        errors = store.validate_settings(
            {"api_base": base, "api_token": token, "user_id": user})
        base_field.error_text = errors.get("api_base")
        user_field.error_text = errors.get("user_id")
        token_field.error_text = errors.get("api_token")
        if errors:
            settings_msg.value = "Fix the highlighted fields."
            page.update()
            return
        store.set_setting(con, "api_base", base)
        store.set_setting(con, "user_id", user)
        if token_state["editing"]:
            store.set_setting(con, "api_token", token)
        refresh_settings()
        refresh_hint()
        settings_msg.value = "Saved ✓"
        page.update()

    gear_btn.on_click = show_settings
    back_btn.on_click = show_home
    token_change_btn.on_click = on_token_change
    save_btn.on_click = on_save

    home_view = ft.Column([], visible=True)
    settings_view = ft.Column([], visible=False)

    def refresh_history() -> None:
        history.controls.clear()
        for _sid, started_at, ended_at in store.list_sessions(con, 10):
            title, subtitle = format_session_row(started_at, ended_at)
            history.controls.append(ft.ListTile(title=title, subtitle=subtitle, dense=True))
        refresh_hint()
        refresh_sync_status()
        try:
            page.update()
        except Exception:
            pass  # ponytail: window already closed, ticker thread exits on stop event

    def set_ui(running: bool) -> None:
        start_btn.disabled = running
        stop_btn.disabled = not running
        status_text.value = "● Recording" if running else "Stopped"
        status_dot.bgcolor = ft.Colors.GREEN if running else ft.Colors.GREY

    def on_start(_=None) -> None:
        if state["running"]:
            return
        if store.validate_settings(current_settings()):
            status_text.value = "Set up settings first (⚙)"
            show_settings()
            return
        timer_label.value = "00:00:00"
        ts = _now()
        state["sid"] = store.start_session(con, ts)
        state["started_at"] = _parse(ts)
        state["running"] = True
        set_ui(True)
        refresh_history()

    def on_stop(_=None) -> None:
        if not state["running"]:
            return
        try:
            store.end_session(con, state["sid"], _now())
        except Exception:
            pass
        state["running"] = False
        state["started_at"] = None
        set_ui(False)
        refresh_history()

    start_btn.on_click = on_start
    stop_btn.on_click = on_stop

    async def ticker() -> None:
        # ponytail: single UI-update point on the page event loop (Flet 1.x
        # page.run_task). Raw threads + page.update() queue/delay updates.
        tick = 0
        while True:
            await asyncio.sleep(1)
            if state["running"] and state["started_at"] is not None:
                elapsed = (datetime.now(timezone.utc) - state["started_at"]).total_seconds()
                timer_label.value = format_hms(elapsed)
                page.update()
            tick += 1
            if tick % 5 == 0:
                refresh_history()

    def on_close(_=None) -> None:
        on_stop()
        stop.set()
        try:
            from . import sync as _sync

            try:
                c = store.pending_counts(con)
                total = c.get("sessions", 0) + c.get("activities", 0) + c.get("screenshots", 0)
            except Exception:
                total = -1
            if total > 0:
                sync_text.value = f"Syncing… {total} items"
                try:
                    page.update()
                except Exception:
                    pass
            remaining = _sync.flush(con, cfg, timeout=30, reason="close")
            if remaining > 0:
                sync_text.value = f"{remaining} items remain, retry next start"
                _snack(page, f"Sync incomplete: {remaining} items will retry next start")
            elif remaining == 0:
                sync_text.value = "✓ synced"
            try:
                last = store.last_sync(con)
                if last and last[6] and ("http 401" in last[6] or "http 403" in last[6]):
                    settings_hint.visible = True
                    settings_hint.value = "Sync unauthorized — check settings (⚙)."
            except Exception:
                pass
            try:
                page.update()
            except Exception:
                pass
        except Exception:
            pass
        try:
            con.close()
        except Exception:
            pass

    page.on_close = on_close
    home_view.controls = [
        ft.Row([gear_btn], alignment=ft.MainAxisAlignment.START),
        timer_label,
        ft.Row([status_dot, status_text],
               alignment=ft.MainAxisAlignment.CENTER),
        sync_text,
        settings_hint,
        ft.Row([start_btn, stop_btn],
               alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        ft.Text("Last tracked times"),
        history,
    ]
    home_view.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    home_view.scroll = ft.ScrollMode.ADAPTIVE
    home_view.expand = True
    settings_view.controls = [
        ft.Row([back_btn, ft.Text("Settings", weight=ft.FontWeight.BOLD)],
               alignment=ft.MainAxisAlignment.START),
        base_field,
        user_field,
        token_field,
        ft.Row([token_change_btn], alignment=ft.MainAxisAlignment.END),
        ft.Row([save_btn], alignment=ft.MainAxisAlignment.CENTER),
        settings_msg,
    ]
    settings_view.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    settings_view.scroll = ft.ScrollMode.ADAPTIVE
    settings_view.expand = True
    page.add(home_view, settings_view)
    refresh_hint()
    refresh_history()
    page.run_task(ticker)


def run() -> None:
    ft.run(main)


if __name__ == "__main__":
    run()
