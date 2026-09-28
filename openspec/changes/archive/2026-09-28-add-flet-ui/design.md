## Context

Current app (`src/worktracker/app.py`) is a pystray tray: Start/Stop/Quit menu plus two daemon threads — a poll loop (`collect.poll()` + `idle.IdleWatcher` + `shots.take()`, intervals from `config.load()`) and `sync.loop()`. State lives in SQLite (`store.py`: `sessions`, `activities`, `screenshots`) under `~/.local/share/worktracker/tracker.db`. There is no visible timer and no history view; users must query the DB.

Constraint from explore: Flet UI **replaces** the tray as the default entrypoint; history is a plain last-sessions list; timer ticks every second; window defaults to ~320x450 and is freely resizable. Ponytail lens applies: reuse store/config/collect/sync as-is, one new UI module, no new tables.

## Goals / Non-Goals

**Goals:**
- One `ft.run()` window showing live elapsed time, Start/Stop, and last 10 sessions.
- Zero change to tracking semantics (5s poll, idle flag, screenshot cadence, offline queue).
- Small default window that resizes gracefully with scrolling history.

**Non-Goals:**
- Totals, charts, per-app breakdowns, search/filter.
- Edit/delete sessions, pause/resume, settings screen.
- Tray fallback, minimize-to-tray, web/PWA build, auth/login.
- Schema migrations (read-only addition of one SELECT helper).

## Decisions

**1. Single-process Flet sharing the worker threads (over separate daemon/service).**
`ui.py:main(page)` loads config, opens the DB, calls the shared `app.start_background_threads(con, cfg, state, stop)` helper (collector `workers()` loop + `sync.loop`, extracted verbatim from `run_tray()`), then builds controls. The helper is used by both tray and Flet frontends — one source of truth, no duplication. Rationale: smallest diff, keeps `python -m worktracker` a single process, avoids IPC. Alternative (UI + headless service) rejected: doubles packaging and adds a protocol for no benefit at this scale.

**2. New `store.list_sessions(con, limit=10)` helper (over raw SQL in UI).**
Returns `(id, started_at, ended_at)` ordered by `id DESC`. Duration and formatting live in UI. Rationale: keeps SQL in `store.py` per existing pattern, UI stays presentation-only. No migration — pure SELECT on existing table.

**3. Timer via 1s UI tick computing `now - started_at` (over Flet animation or backend push).**
On Start, record `started_at` (UTC ISO, same `_now()` helper); an async coroutine driven by `page.run_task()` sleeps 1s, updates the `HH:MM:SS` label and calls `page.update()`, refreshing history every 5th tick — a single UI-update point on the page event loop. (A raw `threading.Thread` ticker was tried first and dropped: on Flet 1.x cross-thread `page.update()` calls queue instead of sending, freezing the counter for seconds.) On Stop, `end_session()` then refresh history; the timer label keeps its final value (frozen) and only resets to `00:00:00` on the next Start. Rationale: trivial, no extra deps, matches the 1s granularity requested. Alternative (sub-second animation) rejected as wasteful.

**4. History refresh on Start/Stop + 5s poll (over live DB watch).**
Refresh the ListView after each control action and on the same 5s cadence as the collector, so a second process writing sessions still shows up. Rationale: cheap (10-row query), no file watchers or triggers.

**5. Layout: single scrollable `Column` — timer, status, buttons, divider, history (over multi-view / tabs).**
Controls: `Text("00:00:00", size=40)`, status `Text` + colored dot (`Container`), `Row[FilledButton Start, OutlinedButton Stop]` with disabled-state toggling, `ListView` of `ListTile(title=start→end, subtitle=duration)`. Window: `page.window.width=320`, `height=450`, `resizable=True`, `scroll=ADAPTIVE`. Column + button rows horizontally centered. Rationale: fits the small-window ask with zero custom styling; Flet handles resize/reflow natively. (`FilledButton` is the Flet 1.x name for the former `ElevatedButton`; entry is `ft.run`, not `ft.app`.)

**6. Entrypoint switch in `app.main()` (over new script).**
`--once` / `--shot` flags unchanged; default path calls `ui.run()` instead of `run_tray()`. `run_tray()` retained but unreferenced (deleted in a follow-up to keep this diff reviewable). `flet` added to `pyproject.toml dependencies`.

## Risks / Trade-offs

- [Risk] Flet/Flutter bundle bloats install + `tools/build.sh` output (100MB+) → Mitigation: pin `flet` version, document in README, no other new deps.
- [Risk] `page.update()` every second causes flicker/CPU on low-end Linux → Mitigation: update only the timer label (not full tree); stop ticking when idle-stopped.
- [Risk] SQLite connection shared between UI thread and worker threads → Mitigation: existing `check_same_thread=False` + short commits retained; UI does only short SELECTs, never long transactions.
- [Risk] Timezone/duration confusion (stored UTC ISO, displayed local) → Mitigation: parse ISO with `fromisoformat`, format display as local `HH:MM` + duration `Xh Ym`; running session shows `… → now`.
- [Risk] X11/Wayland window quirks on Linux → Mitigation: no special perms needed for Flet window itself; collector's Wayland best-effort caveat unchanged.
