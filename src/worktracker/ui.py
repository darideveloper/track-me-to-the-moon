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
    start_btn = ft.FilledButton("Start")
    stop_btn = ft.OutlinedButton("Stop", disabled=True)
    history = ft.ListView(expand=True, spacing=4)

    def refresh_history() -> None:
        history.controls.clear()
        for _sid, started_at, ended_at in store.list_sessions(con, 10):
            title, subtitle = format_session_row(started_at, ended_at)
            history.controls.append(ft.ListTile(title=title, subtitle=subtitle, dense=True))
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
            con.close()
        except Exception:
            pass

    page.on_close = on_close
    page.add(
        ft.Column(
            [
                timer_label,
                ft.Row([status_dot, status_text],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([start_btn, stop_btn],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.Text("Last tracked times"),
                history,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
        )
    )
    refresh_history()
    page.run_task(ticker)


def run() -> None:
    ft.run(main)


if __name__ == "__main__":
    run()
