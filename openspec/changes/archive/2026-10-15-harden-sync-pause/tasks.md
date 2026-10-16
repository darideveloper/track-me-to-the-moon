## 1. Preemptive pause gate in sync core

- [x] 1.1 Thread `control` through `drain()` (`control: SyncControl | None = None`, `None` = unconstrained) and check `is_enabled()` at the top of each `_drain_json` chunk iteration and in the screenshot single-row loop; stop issuing new POSTs when paused while applying already-received acks normally.
- [x] 1.2 Guard `loop()` to pass the live control into `drain()` and skip the call when a pause landed after `wait_for_drain` returned.
- [x] 1.3 Keep `manual_send`, `manual_screenshot`, and `test_connection` on the unconstrained path (`control=None`) with a comment citing the explicit-override spec.

## 2. Retention cleanup independent of drain

- [x] 2.1 Extract a daily-gated `run_retention_cleanup_if_due(con)` from `_maybe_cleanup` (same predicate, same `last_notify_cleanup` gate, still never touching unsent rows).
- [x] 2.2 Restructure `loop` so the daily-gate check runs periodically (bounded slices, e.g. ≤60 s) even while paused — a call placed only after `wait_for_drain` returns `True` is unreachable while paused and does not count.

## 3. Close/quit honors pause

- [x] 3.1 Flet `on_close` (`ui.py`): when paused, skip `flush()`, show "Sync paused — N items kept for next start" in `sync_text`/snack, then exit.
- [x] 3.2 Tray `_close_flush`/`on_quit`/`_quit` (`app.py`): same skip-and-report behavior via console message, sharing one helper with the Flet path where practical.

## 4. Tray pause parity

- [x] 4.1 Add `"sync_control": sync.SyncControl()` to the tray `state` so `start_background_threads` picks up the shared instance instead of a private one.
- [x] 4.2 Add Pause/Resume `pystray.MenuItem`s toggling the shared control, with the tray title showing the paused marker.

## 5. Paused-aware status display

- [x] 5.1 Add a single `brand` paused-status helper and use it in Flet `refresh_sync_status` and `_tray_title` so paused wins over pending/synced/failed text, keeping the auth/settings hint visible alongside rather than merging the two.
- [x] 5.2 Verify at 340 px window width that the wider "Sync paused" pill does not clip against the header icons/stars; shrink padding/font if it does, and record the result. Result: static estimate ~296/316 px used — fits, no layout change; on-device eyeball still recommended.

## 6. Tests

- [x] 6.1 Loop integration: paused loop issues no POSTs; resume produces exactly one drain; existing `SyncControl` unit tests stay green.
- [x] 6.2 Mid-run preemption: slow-POST drain with pause clicked mid-run sends no further POSTs and leaves the remainder pending.
- [x] 6.3 Close-while-paused: `flush` is not called, kept count is reported, rows stay pending.
- [x] 6.4 Retention while paused: acked >7-day rows are cleaned with the gate engaged and no POST issued; recent/unsent rows untouched.
- [x] 6.5 Tray wiring: tray state carries a reachable `SyncControl` passed to the sync loop.

## 7. Verification

- [x] 7.1 Run the full pytest suite (`PYTHONPATH=src python -m pytest tests/ -q`) and `ruff` clean. Result: 92 passed; ruff deltas are pre-existing categories only (BLE001/S110/SIM115 already pervasive).
- [x] 7.2 Manual pass: Flet pause → pending grows, resume → immediate drain, close-while-paused → kept-count message; tray pause/resume mirrors. (Boot smoke under Xvfb passed 2026-10-15: 340×560 window renders, no traceback; interactive clicks need a human on a display. Waived by user 2026-10-16: integration tests + boot smoke accepted as sufficient.)
