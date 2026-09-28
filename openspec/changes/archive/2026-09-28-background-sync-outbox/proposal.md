## Why

Local tracking data (sessions, activities, screenshots) currently piles up in SQLite with no reliable delivery: screenshot-only uploader runs every 60s, activities are never sent, sent/unsent tracking is broken (`synced_activities` table doesn't exist), and closing the app drops pending data. A durable 10-minute background sync with ack-only marking is needed before any backend can be built against it.

## What Changes

- Background sync worker runs every 10 min (±30s jitter) plus a blocking flush on app close (up to 30s with user-visible "Syncing…" message).
- Outbox tracking on all tables: `uploaded`, `upload_attempts`, `last_error`, `uploaded_at` for sessions, activities, screenshots; queries use `WHERE uploaded=0 ORDER BY id ASC`.
- Chunked upload: 100 activities/sessions rows per JSON POST, 1 screenshot per multipart POST, max ~120s per run; leftovers stay pending for next tick.
- Ack-only marking: rows marked `uploaded=1` only on HTTP 200 + valid ack body listing accepted ids; partial acks mark only accepted ids; file delete / cleanup only after ack.
- Failure handling: retry forever (no expiry), 4xx/auth pauses retry with settings hint, system notification max once/day, per-run ledger in `sync_runs`.
- Screenshot retention: keep JPEGs 7 days after ack, then background cleanup deletes files + prunes rows.
- Client-defined backend contract (greenfield): `POST /v1/sessions`, `POST /v1/activities`, `POST /v1/screenshots` with idempotency keys `(user_id, table, local_id)`; single-device assumption.
- SQLite thread-safety via shared lock; fix `pending_activities` ordering bug.

## Capabilities

### New Capabilities

- `background-sync`: 10-min scheduler with jitter, chunked drain (sessions → activities → screenshots), 120s run cap, close-flush with 30s budget and progress message.
- `sync-reliability`: outbox flags + attempts/error columns, ack-only marking with per-item acks, retry-forever policy, once-per-day failure notification, `sync_runs` ledger, 7-day screenshot retention cleanup, SQLite locking fix.

### Modified Capabilities

- None (no existing sync spec; `flet-ui`, `settings-screen`, `settings-storage` untouched).

## Impact

- Affected code: `src/worktracker/store.py` (schema migration, queries), `src/worktracker/sync.py` (rewrite), `src/worktracker/api.py` (typed responses + ack parsing), `src/worktracker/app.py` + `ui.py` (close-flush, notify hook), new `notify.py`, new `cleanup` path.
- New dependency (one): OS toast library (`desktop-notifier` preferred; `plyer` fallback) — or stdlib-only `pystray.notify` if sufficient on all platforms (spike to decide).
- Backend (out of scope to build, in scope to define): contract in design.md that future backend must implement; no breaking change to current offline behavior (offline mode still queues when `api_base` empty).
