## Why

The runtime sync-pause control shipped without a spec (`8efb77e`, `323f08d`) and an audit proved it is not a real gate: in-flight drains keep uploading for up to ~2 minutes after pause, close/quit flush silently overrides it, the tray frontend has no pause at all, and the daily screenshot-retention cleanup stalls while paused. Specifying and hardening the gate now restores the "keep data local" promise before users rely on it.

## What Changes

- Pause becomes preemptive at chunk boundaries: an in-flight `drain()` stops issuing new POSTs once paused (already-accepted chunks stay marked; unstarted chunks stay pending).
- Close/quit honors pause: when paused, the blocking 30s flush is skipped and the UI/console reports "paused — N items kept for next start" instead of uploading.
- Tray frontend gets pause parity: shared `SyncControl` instance plus a pause/resume menu item and pending/paused title suffix.
- Screenshot-retention cleanup is decoupled from `drain()` so the 7-day daily pass still runs while paused.
- Status distinguishes paused from stalled: header/tray show an explicit paused state instead of bare "N pending".
- Manual Debug sends (`Send all` / per-table / screenshot) remain an explicit user override and bypass pause; this is documented, not changed.
- Coverage: loop-skips-while-paused, resume-drains-once, pause-mid-run-stops-new-POSTs, close-flush-respects-pause, tray wiring; the existing `SyncControl`-only unit tests stay green.

## Capabilities

### New Capabilities

- `sync-pause`: runtime pause gate semantics — what pause blocks (scheduled ticks, in-flight chunks, close flush), what it never blocks (local capture, manual sends), resume-drains-immediately, runtime-only reset-to-enabled on start, and paused status display in both frontends.

### Modified Capabilities

- `background-sync`: close-flush requirement gains the paused exemption (skip flush, report kept count).
- `sync-reliability`: screenshot-retention requirement gains independence from drain cadence (cleanup runs while paused).

## Impact

- `src/moon_tracker/sync.py` (`SyncControl`, `loop`, `drain`, `_drain_json`, screenshot stage, `flush`, cleanup entry point).
- `src/moon_tracker/ui.py` (`on_close` flush path, sync pill, status text).
- `src/moon_tracker/app.py` (tray state, menu, `_close_flush`, `_tray_title` call sites).
- `src/moon_tracker/brand.py` (paused status helper, if needed).
- `tests/test_sync.py` plus new pause-integration tests; no DB migration, no API/backend changes, no config format changes.
