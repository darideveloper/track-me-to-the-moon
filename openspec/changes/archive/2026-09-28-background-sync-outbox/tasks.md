## 1. Store migration + outbox queries

- [x] 1.1 Add `uploaded`, `upload_attempts`, `last_error`, `uploaded_at` columns (idempotent ALTER) + `sync_runs` table + pending indexes in `store.py`
- [x] 1.2 Rewrite `pending_sessions` / `pending_activities` / `pending_screenshots` as `WHERE uploaded=0 ORDER BY id ASC LIMIT N`; remove `synced_activities` path
- [x] 1.3 Add `mark_uploaded(table, ids)`, `note_error(table, ids, err)`, `log_sync_run(...)` helpers transacted under a module-level `threading.Lock` in `store.py` (no `connect()` signature change)
- [x] 1.4 Add/extend `tests/test_store.py` for migration idempotency, oldest-first order, ack-only marking, partial ack

## 2. API client with ack parsing

- [x] 2.1 Change `api.py` to return typed results (`ok`, `accepted_ids`, `retryable`, `error`) instead of bare bool; parse `{ ok, accepted }`
- [x] 2.2 Add `post_sessions` alongside `post_activities`; add `client_id` (`{table}:{id}`) to every payload; keep `TIMEOUT=15`
- [x] 2.3 Classify 5xx/timeout/429 as retryable, other 4xx as auth-pause; unit-test with mocked `requests`

## 3. Sync engine rewrite

- [x] 3.1 Rewrite `sync.py`: `loop(stop, interval=600+jitter)` draining sessions → activities (100/chunk) → screenshots (1-by-1), run cap ~120s/10 chunks
- [x] 3.2 Implement `flush(timeout=30, reason)` used by close paths; stop collector first, hard deadline, return remaining count
- [x] 3.3 Add daily screenshot cleanup (acked + 7d → delete file + row); never delete unsent files
- [x] 3.4 Spike-test notifier choice (`desktop-notifier` vs `plyer` vs `pystray.notify`) on target OS, then implement `notify.py` shim with 1/day throttle

## 4. App + UI wiring

- [x] 4.1 Wire `app.py:on_quit` (+SIGTERM/SIGINT) to stop collector, `flush(30)` with console message, then close DB
- [x] 4.2 Wire `ui.py:on_close` to `flush(30)` with Flet progress dialog/snackbar, settings hint on 4xx
- [x] 4.3 Add pending-count indicator + last-sync status to tray title / Flet status row (reads ledger, no extra thread)

## 5. Verification

- [x] 5.1 Run `pytest`, `ruff`; manual pass: offline queue → online drain → kill -9 mid-run → restart shows no dupes on backend log
- [x] 5.2 Manual close test: backlog drains ≤30s with message; failure test: 3 failed ticks → exactly 1 OS toast that day
