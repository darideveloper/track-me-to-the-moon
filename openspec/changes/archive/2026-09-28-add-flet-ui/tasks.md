## 1. Store and dependencies

- [x] 1.1 Add `store.list_sessions(con, limit=10)` returning `(id, started_at, ended_at)` newest-first
- [x] 1.2 Add `flet` to `pyproject.toml` dependencies (pinned) and verify `pip install -e .` resolves
- [x] 1.3 Add/extend `tests/test_store.py` coverage for `list_sessions` ordering and open-session (`ended_at IS NULL`) row

## 2. Flet UI core

- [x] 2.1 Create `src/worktracker/ui.py` with `ft.run()` entry `run()`: window 320x450, resizable, centered scrollable Column layout
- [x] 2.2 Implement timer label (`HH:MM:SS`), status indicator, and 1s tick via `page.run_task()` async coroutine (single UI-update point; freezes on Stop, resets on next Start)
- [x] 2.3 Implement Start/Stop buttons wired to `store.start_session` / `store.end_session` with disabled-state toggling
- [x] 2.4 Implement history ListView (last 10 via `list_sessions`): start/end/duration formatting, open-session `→ now` marker, refresh on Start/Stop + 5s poll
- [x] 2.5 Extract shared `app.start_background_threads()` (collector `workers()` loop + uploader) used by both tray and Flet, with clean shutdown on window close (`on_close`: end session, set stop, close DB)
- [x] 2.6 Add `tests/test_ui_format.py` unit tests for `format_hms` / `format_duration` / `format_session_row` (closed + running rows)

## 3. Entrypoint and docs

- [x] 3.1 Switch `app.main()` default path from `run_tray()` to `ui.run()`, keeping `--once` / `--shot` flags unchanged
- [x] 3.2 Update `README.md` quickstart for Flet launch (`python -m worktracker`) and note tray replacement
- [x] 3.3 Smoke-test on Linux (headless logic smoke: timer format, history rows, collector writes activities; manual window open still pending on a machine with display)

## 4. Verification

- [x] 4.1 Run `pytest` green
- [x] 4.2 Run `ruff` on touched files: no new violation types (repo has pre-existing EXE002/BLE001/S110 debt, left untouched)
