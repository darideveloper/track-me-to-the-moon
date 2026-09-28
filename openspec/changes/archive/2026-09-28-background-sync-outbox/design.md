## Context

`store.py` holds sessions/activities/screenshots in SQLite (WAL) shared between collector thread (`app.workers`) and uploader thread (`sync.loop`). Current uploader sends only screenshots every 60s with exponential backoff, uses a single `uploaded` flag on screenshots, and has a broken `pending_activities` path referencing a nonexistent `synced_activities` table with `ORDER BY id DESC`. `api.py` returns bare `r.ok`. Close paths (`app.on_quit`, `ui.on_close`) drop pending data. No notifier, no ledger, no lock around the shared connection.

Stakeholders: employee running tracker (needs non-blocking UI, close in ≤30s, at most 1 notification/day), future backend team (needs a stable contract to build to). Single-device assumption; `user_id` + local row id is the idempotency key.

## Goals / Non-Goals

**Goals:**
- Durable outbox: every session/activity/screenshot eventually delivered exactly-once (via idempotent retry), marked sent only on valid ack.
- Predictable cadence: 10-min tick with jitter + close-flush; each run bounded (~120s) via small chunks (100 JSON rows, 1 shot).
- Operable failures: retry forever, distinguish retryable (5xx/timeout) vs auth (4xx), notify ≤1/day, ledger every run.

**Non-Goals:**
- Building the backend (only defining its contract).
- Real-time streaming, conflict resolution, multi-device merge.
- Encryption-at-rest, screenshot redaction, bandwidth throttling UI.

## Decisions

**1. Flags on existing tables over a generic outbox table.**
`ALTER TABLE {sessions,activities,screenshots} ADD COLUMN uploaded INTEGER DEFAULT 0, upload_attempts INTEGER DEFAULT 0, last_error TEXT DEFAULT '', uploaded_at TEXT`. Why: smallest migration, keeps existing queries readable, no data copy. Alternative (single `outbox` JSON table) rejected: harder to query/debug, bigger rewrite.

**2. Drain order sessions → activities → screenshots, oldest-first.**
`WHERE uploaded=0 ORDER BY id ASC LIMIT N`. Why: FK order (backend needs session before its rows), oldest-first fixes today's newest-first bug and bounds backlog age. Screenshots last because they dominate run time.

**3. Chunk sizes 100 JSON / 1 shot, run cap ~120s or 10 chunks.**
Why: user chose "smaller chunks"; 100 activities ≈ 30–80KB, well under timeout on slow links; 1 shot per POST avoids multipart+JSON mixing that causes timeouts. Leftover rows simply wait for next tick — no timeout cascade. Alternative (300/chunk) rejected per user input.

**4. Ack contract: HTTP 200 + `{ ok:true, accepted:[client_ids] }`.**
`client_id` = `{table}:{id}` (e.g. `activity:412`), sent per row; backend echoes accepted ids. Only accepted ids get `uploaded=1, uploaded_at=now` in the same transaction as the ledger insert. Partial acks mark partial progress; `ok:false` or id mismatch marks nothing. `r.ok`-only (today) rejected: masks partial/duplicate acceptance. 4xx (except 429) → pause + surface settings hint, don't hot-retry; 5xx/timeout/429 → retryable.

**5. Scheduler: `SYNC_INTERVAL_SEC=600` + `±30s` jitter, close-flush 30s.**
`sync.loop(stop)` waits on event with jittered interval; `flush(timeout=30, reason="close")` called from `on_quit`/`on_close` after stopping collector, with UI message ("Syncing… <n> items left") and hard deadline — then exit regardless. Why: meets "send on close" without hanging the OS; jitter avoids fleet stampede later.

**6. Notifications: single `notify.py` shim, throttled 1/day.**
Tray mode uses `pystray.Icon.notify`; Flet mode uses OS toast via `desktop-notifier` (preferred pure-Python, no dbus CLI dep) with `plyer` fallback; spike at implementation to confirm Linux/Win/macOS. Throttle key = `last_notify_date + kind` in settings table. In-app `SnackBar`/status text mirrors toast when window open.

**7. Retention: keep shots 7 days post-ack, retry-forever otherwise.**
Cleanup pass (piggybacked on sync tick, daily) deletes JPEG files with `uploaded=1 AND uploaded_at < now-7d` then deletes their rows. Unsent rows never expire (user: retry forever). Why: bounds disk without losing evidence; explicit user choice over TTL-drop.

**8. Thread-safety: one module-level `threading.Lock` guarding all `con` access.**
`store.py` owns a shared lock; every helper acquires it internally so existing `connect()` callers (`app.py`, `ui.py`, tests) keep working unchanged. Why: `check_same_thread=False` alone is unsafe; a module lock is cheaper than a queue refactor and avoids a breaking signature change.

## Risks / Trade-offs

- [Risk] Close-flush overruns 30s on huge backlog → Mitigation: hard deadline, oldest-first so most valuable (oldest) goes first, message shows remaining count.
- [Risk] Backend implements all-or-nothing instead of per-item acks → Mitigation: client treats missing `accepted` as all-or-nothing fallback (if `ok:true` + no list → mark whole chunk).
- [Risk] Disk growth offline for weeks (retry-forever) → Mitigation: activities are tiny; shots are ~100–300KB each at q60 — 7-day post-ack cleanup + monitor pending count in ledger; document capacity.
- [Risk] `desktop-notifier` unavailable on some Linux → Mitigation: fallback chain notifier → pystray.notify → log-only; spike first.
- [Risk] Migration on existing DBs with pending screenshots → Mitigation: `ADD COLUMN IF NOT EXISTS` pattern (try/except), backfill `uploaded=0`; no data loss.
- [Trade-off] Retry-forever vs spam: throttle hides persistent failure → Mitigation: settings hint stays visible + ledger queryable; daily toast is reminder, not blocker.

## Migration Plan

1. Schema migration runs inside `store.connect` (idempotent `ALTER TABLE`, create `sync_runs`, create index `idx_activities_pending`, `idx_screenshots_pending`).
2. Deploy client first; backend implements contract after (no version coupling — offline queues until `api_base` set).
3. Rollback: new columns ignored by old code; old uploader would still send screenshots (harmless, idempotent via `client_id` if backend already dedupes).

## Open Questions

- None blocking. Spike (in tasks): confirm `desktop-notifier` vs `plyer` on target OSes; confirm JPEG avg size to validate 120s budget.

## Backend contract (client-defined, for backend team)

- `POST {base}/v1/sessions` body `{ items: [{ client_id, session_id, started_at, ended_at }] }`
- `POST {base}/v1/activities` body `{ items: [{ client_id, session_id, ts, app, title, idle }] }`
- `POST {base}/v1/screenshots` multipart `file` + fields `{ client_id, session_id, ts, user_id }`
- Auth `Authorization: Bearer <token>`; success `200 { "ok": true, "accepted": ["activity:1", ...] }`; error `4xx/5xx { "ok": false, "error": "..." }`.
- Server MUST dedupe on `(user_id, client_id)` and return already-seen ids in `accepted`.
