## Why

The tracker is currently tray-only (pystray Start/Stop/Quit) with no visible timer or history. Users can't see elapsed time or recent sessions without querying SQLite directly, which hurts trust and daily use.

## What Changes

- Add a small Flet desktop window as the primary UI, replacing `run_tray()` as the default entrypoint.
- Live timer display (`HH:MM:SS`, ticks every 1s) with Recording/Stopped status indicator.
- Start / Stop buttons wired to existing `store.start_session()` / `store.end_session()`.
- "Last tracked times" list showing the 10 most recent sessions (start, end, duration), auto-refreshed on Start/Stop and every 5s.
- Default window ~320x450, freely resizable, horizontally centered controls, history area scrolls.
- Add `flet` (pinned `flet==1.0.1`) to `pyproject.toml` dependencies.
- **BREAKING**: default `python -m worktracker` launches Flet UI instead of pystray tray. Tray code retained but no longer invoked (removal deferred to keep this change small).

## Capabilities

### New Capabilities

- `flet-ui`: Flet desktop window with live timer, Start/Stop controls, recent-sessions list, and small resizable window behavior.

### Modified Capabilities

- None. Existing `store` sessions/activities/screenshots behavior is unchanged; UI is a new frontend on the same SQLite schema.

## Impact

- Affected code: new `src/worktracker/ui.py`, `app.py` (shared `start_background_threads()` + entrypoint switch), `store.py` (`list_sessions`), `pyproject.toml` (new `flet` dep), `README.md` quickstart, `tests/` (`test_store.py` additions + new `test_ui_format.py`).
- Collector/uploader logic (`collect`, `idle`, `shots`, `sync`) unchanged, shared by tray and Flet via the helper.
- New `store.list_sessions(limit)` read query; no schema migration.
- Packaging: `tools/build.sh` output grows (Flutter bundle via Flet); Linux X11 still recommended, no permission changes.
