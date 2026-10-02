## 1. Event bus + log core

- [x] 1.1 Add `ApiEvent` dataclass + `emit` hook in `api.py` (`_post_json`, `post_screenshot`) with 2KB/1KB truncation and token redaction
- [x] 1.2 Add in-memory `debuglog` ring (`deque(maxlen=200)`, thread-safe append/drain/clear, bundle formatter with version + pending + last sync)
- [x] 1.3 Thread `emit` + `tables` filter + `reason="manual"` through `sync.drain`/`_drain_json` without changing ack/marking semantics
- [x] 1.4 Add unit tests: emit on ok/401/timeout, truncation marker, redaction, per-type filter drains only selected tables, ring cap at 200

## 2. Manual actions (backend)

- [x] 2.1 Implement `manual_screenshot(con, cfg, state)` = resolve target sid (active else most recent via `list_sessions`, refuse with Launch-first hint when none) + `shots.take()` + `store.add_screenshot()` + screenshots-stage drain
- [x] 2.2 Implement `manual_send(con, cfg, tables)` in worker thread with UI-only busy guard (disables manual buttons while in flight; scheduled tick may still interleave — harmless via idempotent `client_id`)
- [x] 2.3 Implement `test_connection(cfg)` as `GET {base}/health` then empty `POST /v1/sessions` probe fallback, logged but never marked uploaded
- [x] 2.4 Add tests for stopped-state actions (no session required) and clear-log-never-touches-outbox

## 3. Flet debug view

- [x] 3.1 Add brand-matched header debug `IconButton` + third `debug_view` (show/hide like settings, back button, timer-safe)
- [x] 3.2 Build actions grid: [📸 Screenshot] [Sessions][Activities][Screenshots][Send all] [🧪 Test] with disabled-while-busy state
- [x] 3.3 Build log `ListView` newest-first, compact rows + tap-to-expand previews, ticker-polled refresh (≤2s) when visible, cap visible render at 60 + show-more
- [x] 3.4 Wire [Copy bundle] (`page.clipboard.set()` async + read-only TextField fallback) + [Clear] + SnackBar confirmations; verify 340x560 scroll

## 4. Verify

- [x] 4.1 Run `uv run --frozen --extra dev pytest` green (new + existing `test_sync.py`, `test_api.py` suites)
- [x] 4.2 Manual pass: launch UI, open debug, screenshot now, per-type sends, test ping, force 401 (bad token) and confirm error row + redaction, copy bundle paste check
- [x] 4.3 Confirm no regression: 10-min tick, close flush, history moon dots, settings validation unchanged
