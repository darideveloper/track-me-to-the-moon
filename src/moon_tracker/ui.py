"""Flet desktop UI: Track Me to the Moon — night-sky header, eclipse toggle, history."""
from __future__ import annotations

import asyncio
import os
import sys
import threading
from datetime import datetime, timezone

import flet as ft

from . import brand, config, debuglog, desktop_entry, store
from . import version as _version
from .app import _now, start_background_threads


def version_footer_text() -> str:
    """Footer string for the tracker window (runtime version, `unknown` fallback)."""
    return _version.get_version()


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


# Eclipse toggle geometry (C×D pill).
_TRACK_W, _TRACK_H, _KNOB, _PAD = 280, 64, 56, 4
_KNOB_LEFT = _PAD
_KNOB_RIGHT = _TRACK_W - _KNOB - _PAD


def main(page: ft.Page, data_dir=None) -> None:
    ddir = config.data_dir(data_dir)
    dev = not config.is_default_dir(ddir)
    label = config.short_label(ddir) if dev else ""
    cfg = config.load()
    con = store.connect(ddir / "tracker.db")
    state = {"running": False, "sid": None, "started_at": None}
    stop = threading.Event()
    start_background_threads(con, cfg, state, stop, ddir)

    page.title = brand.DISPLAY_NAME + (f" [🧪 {label}]" if dev else "")
    page.theme, page.dark_theme = brand.page_themes()
    page.theme_mode = ft.ThemeMode.SYSTEM
    if page.window is not None:
        page.window.width = 340
        page.window.height = 560
        page.window.resizable = True
        try:
            page.window.icon = str(brand.asset_path(desktop_entry.platform_icon_name()))
        except Exception:
            pass  # ponytail: icon is decoration, never break startup

    # --- Night-sky header (always deep navy = brand anchor in both modes) ---
    header_moon = ft.Text(brand.MOON_STOPPED, size=44, color=brand.MOON_WHITE,
                          text_align=ft.TextAlign.CENTER)
    stars = ft.Text("✦   ·   ✦   ·   ✦", size=10, color=brand.NIGHT_STAR,
                    text_align=ft.TextAlign.CENTER)
    timer_label = ft.Text("00:00:00", size=36, weight=ft.FontWeight.BOLD,
                          color=brand.MOON_WHITE, font_family="monospace",
                          text_align=ft.TextAlign.CENTER)
    status_dot = ft.Container(width=12, height=12, border_radius=6, bgcolor=ft.Colors.GREY)
    status_text = ft.Text("Stopped", color=brand.MOON_WHITE, size=13)
    sync_text = ft.Text("", size=11, color=brand.DARK_MUTED, text_align=ft.TextAlign.CENTER)
    theme_btn = ft.IconButton(icon=ft.Icons.DARK_MODE, tooltip="Toggle light / dark",
                              icon_color=brand.MOON_WHITE)
    gear_btn = ft.IconButton(icon=ft.Icons.SETTINGS, tooltip="Settings",
                             icon_color=brand.MOON_WHITE)
    debug_btn = ft.IconButton(icon=ft.Icons.BUG_REPORT, tooltip="Debug: API log + manual send",
                              icon_color=brand.MOON_WHITE)
    header = ft.Container(
        bgcolor=brand.NIGHT_SKY, border_radius=16, padding=12,
        content=ft.Column([
            ft.Row([ft.Row([gear_btn, debug_btn], spacing=0), stars, theme_btn],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            header_moon,
            timer_label,
            ft.Row([status_dot, status_text],
                   alignment=ft.MainAxisAlignment.CENTER),
            sync_text,
        ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
    )

    # --- Eclipse toggle (C): sliding moon knob on a pill track ---
    knob_label = ft.Text(brand.MOON_STOPPED, size=26, color=brand.MOON_WHITE,
                          text_align=ft.TextAlign.CENTER)
    knob = ft.Container(width=_KNOB, height=_KNOB, left=_KNOB_LEFT, top=_PAD,
                        shape=ft.BoxShape.CIRCLE, bgcolor=ft.Colors.GREY_700,
                        alignment=ft.Alignment.CENTER, content=knob_label,
                        animate_position=300, ignore_interactions=True)
    toggle_caption = ft.Text(brand.LAUNCH_LABEL, size=13, tooltip=brand.LAUNCH_TOOLTIP,
                             text_align=ft.TextAlign.CENTER)
    track_label = ft.Container(alignment=ft.Alignment.CENTER,
                               content=ft.Text("○ ────────── ●", size=10,
                                               color=ft.Colors.GREY))
    track = ft.Container(width=_TRACK_W, height=_TRACK_H, border_radius=32,
                         border=ft.Border.all(1, ft.Colors.OUTLINE),
                         content=ft.Stack([track_label, knob]))
    toggle_icon = ft.Icon(ft.Icons.FLIGHT_TAKEOFF, size=16, color=ft.Colors.GREY)

    settings_hint = ft.Text("Settings incomplete — open ⚙ to finish setup.",
                            size=12, visible=False, color=ft.Colors.AMBER)
    history = ft.ListView(expand=True, spacing=4)
    footer_text = version_footer_text() + (f" · {ddir}" if dev else "")
    version_footer = ft.Text(footer_text, size=10,
                             color=brand.DARK_MUTED,
                             text_align=ft.TextAlign.CENTER)

    def current_settings() -> dict:
        return store.get_settings_dict(con)

    def refresh_hint() -> None:
        settings_hint.visible = bool(store.validate_settings(current_settings()))

    def refresh_sync_status() -> None:
        """Pending count + last-sync status (reads ledger, no extra thread)."""
        try:
            c = store.pending_counts(con)
            total = brand.pending_total(c)
            last = store.last_sync(con)
            err = last[6] if last else None
            st = brand.sync_state(total, err)
            if st == "pending":
                sync_text.value = f"{brand.MOON_PENDING} {total} pending"
            elif st == "failed":
                sync_text.value = f"⚠ last sync failed: {(err or '')[:60]}"
            elif st == "synced":
                sync_text.value = f"{brand.MOON_SYNCED} synced"
            else:
                sync_text.value = ""
        except Exception:
            sync_text.value = ""

    def refresh_header() -> None:
        running = state["running"]
        header_moon.value = brand.header_moon(running)
        knob_label.value = brand.header_moon(running)
        knob.left = _KNOB_RIGHT if running else _KNOB_LEFT
        knob.bgcolor = brand.ACCENT_SKY if running else ft.Colors.GREY_700
        status_text.value = "● Recording" if running else "Stopped"
        status_dot.bgcolor = brand.ACCENT_SKY if running else ft.Colors.GREY
        toggle_caption.value = brand.LAND_LABEL if running else brand.LAUNCH_LABEL
        toggle_caption.tooltip = brand.LAND_TOOLTIP if running else brand.LAUNCH_TOOLTIP
        toggle_icon.name = ft.Icons.FLIGHT_LAND if running else ft.Icons.FLIGHT_TAKEOFF

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
        debug_view.visible = False
        settings_view.visible = True
        page.update()

    def show_home(_=None) -> None:
        settings_view.visible = False
        debug_view.visible = False
        home_view.visible = True
        refresh_hint()
        page.update()

    def show_debug(_=None) -> None:
        home_view.visible = False
        settings_view.visible = False
        debug_view.visible = True
        refresh_debug_log()
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

    def on_theme_toggle(_=None) -> None:
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            theme_btn.icon = ft.Icons.DARK_MODE
        else:
            page.theme_mode = ft.ThemeMode.DARK
            theme_btn.icon = ft.Icons.LIGHT_MODE
        page.update()

    theme_btn.on_click = on_theme_toggle

    # --- Debug view: manual actions + live API log (session-only ring) ---
    debug_log = ft.ListView(expand=True, spacing=2)
    debug_msg = ft.Text("", size=12)
    debug_count = ft.Text("", size=11, color=brand.DARK_MUTED)
    debug_bundle_field = ft.TextField(label="Debug bundle (copy manually if clipboard fails)",
                                      multiline=True, read_only=True, visible=False,
                                      min_lines=4, max_lines=8, dense=True)
    debug_back_btn = ft.TextButton("‹ Back")
    debug_busy = {"on": False}
    debug_result = {"msg": None}
    debug_show_all = {"on": False}

    shot_btn = ft.FilledButton("📸 Screenshot")
    sess_btn = ft.OutlinedButton("Sessions")
    act_btn = ft.OutlinedButton("Activities")
    shots_btn = ft.OutlinedButton("Screenshots")
    send_all_btn = ft.OutlinedButton("Send all")
    ping_btn = ft.OutlinedButton("🧪 Test")
    copy_btn = ft.TextButton("Copy bundle")
    clear_btn = ft.TextButton("Clear")
    show_more_btn = ft.TextButton("Show more")
    _debug_buttons = [shot_btn, sess_btn, act_btn, shots_btn, send_all_btn, ping_btn]

    def _set_debug_busy(busy: bool) -> None:
        debug_busy["on"] = busy
        for b in _debug_buttons:
            b.disabled = busy
        try:
            page.update()
        except Exception:
            pass

    def refresh_debug_log() -> None:
        """Render newest-first log rows (ticker-polled, page-loop only)."""
        try:
            events = debuglog.recent(200)
        except Exception:
            events = []
        debug_count.value = f"API calls this session: {len(events)}" if events else "No API calls yet"
        debug_log.controls.clear()
        visible = events if debug_show_all["on"] else events[:60]
        for e in visible:
            try:
                title = debuglog.compact(e)
            except Exception:
                title = "api event"
            req = str(getattr(e, "req_preview", "") or "")
            res = str(getattr(e, "res_preview", "") or "")
            details = []
            if req:
                details.append(ft.Text(f"req: {req}", size=10, selectable=True))
            if res:
                details.append(ft.Text(f"res: {res}", size=10, selectable=True))
            if not details:
                details.append(ft.Text("no payload", size=10))
            dot = "🟢" if getattr(e, "ok", False) else ("⚪" if getattr(e, "status", None) is None else "🔴")
            debug_log.controls.append(ft.ExpansionTile(
                title=ft.Text(f"{dot} {title}", size=11),
                controls=details, dense=True))
        show_more_btn.visible = len(events) > 60 and not debug_show_all["on"]
        if debug_result["msg"] is not None:
            debug_msg.value = debug_result["msg"]
            debug_result["msg"] = None
            _set_debug_busy(False)
            refresh_sync_status()
            try:
                page.update()
            except Exception:
                pass

    def _run_manual(kind: str, tables=None):
        if debug_busy["on"]:
            return
        _set_debug_busy(True)
        debug_msg.value = "Working…"
        try:
            page.update()
        except Exception:
            pass

        def work() -> None:
            try:
                from . import sync as _sync

                if kind == "shot":
                    _status, msg, _stats = _sync.manual_screenshot(con, cfg, state,
                                                                   data_dir=ddir)
                elif kind == "ping":
                    res = _sync.test_connection(con)
                    label = res.status if res.status is not None else res.error
                    msg = f"Ping: {label}" if res.ok else f"Ping failed: {label}"
                else:
                    stats = _sync.manual_send(con, cfg, tables)
                    msg = (f"Sent sessions/activities/shots="
                           f"{stats['sent_sessions']}/{stats['sent_activities']}/"
                           f"{stats['sent_screenshots']}")
                    if stats.get("skipped"):
                        msg += " (skipped: no api_base)"
                    elif stats.get("error"):
                        msg += f" — {stats['error'][:80]}"
                debug_result["msg"] = msg
            except Exception as ex:  # never kill the worker on UI errors
                debug_result["msg"] = f"Failed: {ex}"

        threading.Thread(target=work, daemon=True).start()

    def on_shot(_=None) -> None:
        _run_manual("shot")

    def on_send_sessions(_=None) -> None:
        _run_manual("sessions", ("sessions",))

    def on_send_activities(_=None) -> None:
        _run_manual("activities", ("activities",))

    def on_send_shots(_=None) -> None:
        _run_manual("shots", ("screenshots",))

    def on_send_all(_=None) -> None:
        _run_manual("all", ("sessions", "activities", "screenshots"))

    def on_ping(_=None) -> None:
        _run_manual("ping")

    def on_show_more(_=None) -> None:
        debug_show_all["on"] = True
        refresh_debug_log()
        try:
            page.update()
        except Exception:
            pass

    async def on_copy(_=None) -> None:
        try:
            bundle = debuglog.format_bundle(
                version_footer_text(), store.pending_counts(con),
                store.last_sync(con), debuglog.recent(), ddir)
        except Exception as ex:
            _snack(page, f"Bundle failed: {ex}")
            return
        copied = False
        try:
            svc = getattr(page, "clipboard", None)
            if svc is not None:
                await svc.set(bundle)
                copied = True
        except Exception:
            copied = False
        if copied:
            _snack(page, "Debug bundle copied ✓")
        else:
            debug_bundle_field.value = bundle
            debug_bundle_field.visible = True
            _snack(page, "Clipboard unavailable — bundle shown below, select & copy")
        try:
            page.update()
        except Exception:
            pass

    def on_clear(_=None) -> None:
        debuglog.clear()
        debug_show_all["on"] = False
        debug_bundle_field.visible = False
        refresh_debug_log()
        _snack(page, "Log cleared (outbox untouched)")
        try:
            page.update()
        except Exception:
            pass

    debug_back_btn.on_click = show_home
    debug_btn.on_click = show_debug
    shot_btn.on_click = on_shot
    sess_btn.on_click = on_send_sessions
    act_btn.on_click = on_send_activities
    shots_btn.on_click = on_send_shots
    send_all_btn.on_click = on_send_all
    ping_btn.on_click = on_ping
    copy_btn.on_click = on_copy
    clear_btn.on_click = on_clear
    show_more_btn.on_click = on_show_more

    home_view = ft.Column([], visible=True)
    settings_view = ft.Column([], visible=False)
    debug_view = ft.Column([], visible=False)

    def refresh_history() -> None:
        history.controls.clear()
        rows = store.list_sessions(con, 10)
        try:
            any_pending = brand.pending_total(store.pending_counts(con)) > 0
        except Exception:
            any_pending = False
        if not rows:
            history.controls.append(ft.Text("No sessions yet — tap the moon to launch 🚀",
                                           size=13, text_align=ft.TextAlign.CENTER))
        for row in rows:
            _sid, started_at, ended_at = row[0], row[1], row[2]
            uploaded = row[3] if len(row) > 3 else None
            title, subtitle = format_session_row(started_at, ended_at)
            glyph = brand.row_moon(bool(uploaded) if uploaded is not None else None,
                                   any_pending)
            history.controls.append(ft.ListTile(leading=ft.Text(glyph, size=20),
                                                title=ft.Text(title),
                                                subtitle=ft.Text(subtitle), dense=True))
        refresh_hint()
        refresh_sync_status()
        refresh_header()
        try:
            page.update()
        except Exception:
            pass  # ponytail: window already closed, ticker thread exits on stop event

    def set_ui(running: bool) -> None:
        refresh_header()

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

    def on_toggle(_=None) -> None:
        if state["running"]:
            on_stop()
        else:
            on_start()

    track.on_click = on_toggle

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
            if tick % 2 == 0:
                try:
                    if debug_view.visible:
                        refresh_debug_log()
                        page.update()
                except Exception:
                    pass

    def on_close(_=None) -> None:
        on_stop()
        stop.set()
        try:
            from . import sync as _sync

            try:
                total = brand.pending_total(store.pending_counts(con))
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
                sync_text.value = f"{brand.MOON_SYNCED} synced"
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
        header,
        ft.Row([toggle_icon, toggle_caption],
               alignment=ft.MainAxisAlignment.CENTER),
        track,
        settings_hint,
        ft.Divider(),
        ft.Text("Last tracked times"),
        history,
        version_footer,
    ]
    home_view.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    home_view.scroll = ft.ScrollMode.ADAPTIVE
    home_view.expand = True
    settings_view.controls = [
        ft.Row([back_btn, ft.Text("Settings", weight=ft.FontWeight.BOLD)],
               alignment=ft.MainAxisAlignment.START),
        ft.Card(content=ft.Container(
            padding=12,
            content=ft.Column([base_field, user_field, token_field,
                               ft.Row([token_change_btn],
                                      alignment=ft.MainAxisAlignment.END),
                               ft.Row([save_btn],
                                      alignment=ft.MainAxisAlignment.CENTER),
                               settings_msg], spacing=8),
        )),
    ]
    settings_view.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    settings_view.scroll = ft.ScrollMode.ADAPTIVE
    settings_view.expand = True
    debug_view.controls = [
        ft.Row([debug_back_btn, ft.Text("Debug: API + manual send",
                                        weight=ft.FontWeight.BOLD)],
               alignment=ft.MainAxisAlignment.START),
        ft.Card(content=ft.Container(
            padding=12,
            content=ft.Column([
                ft.Row([shot_btn, ping_btn],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([sess_btn, act_btn],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([shots_btn, send_all_btn],
                       alignment=ft.MainAxisAlignment.CENTER),
                debug_msg,
            ], spacing=8),
        )),
        ft.Row([debug_count,
                ft.Row([copy_btn, clear_btn],
                       alignment=ft.MainAxisAlignment.END)],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        debug_log,
        show_more_btn,
        debug_bundle_field,
    ]
    debug_view.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    debug_view.scroll = ft.ScrollMode.ADAPTIVE
    debug_view.expand = True
    page.add(home_view, settings_view, debug_view)
    refresh_header()
    refresh_hint()
    refresh_history()
    page.run_task(ticker)


def run(data_dir=None) -> None:
    import functools

    ddir = config.data_dir(data_dir)
    dev = not config.is_default_dir(ddir)
    if sys.platform == "linux":
        try:
            os.environ.setdefault("FLET_APP_ID", desktop_entry.APP_ID)
            if not dev:
                desktop_entry.patch_client_icon()
                desktop_entry.ensure_installed(desktop_entry.repo_root())
        except Exception:
            pass  # ponytail: icon is decoration, never break startup
    elif sys.platform == "darwin":
        try:
            if not dev:
                desktop_entry.ensure_macos_bundle_icon()
        except Exception:
            pass  # ponytail: icon is decoration, never break startup
    ft.run(functools.partial(main, data_dir=ddir))


if __name__ == "__main__":
    run()
