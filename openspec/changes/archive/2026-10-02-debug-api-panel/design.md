## Context

Collector (`app.py:start_background_threads`) polls every 5s and screenshots every ~5min into SQLite outbox (`uploaded=0`). Sync thread (`sync.py:loop`) drains every 600s±30s via `api.post_*` (`/v1/sessions`, `/v1/activities`, `/v1/screenshots`) with ack-only marking and one `sync_runs` ledger row per run. Flet UI (`ui.py`) has two views (home, settings) plus a 1s ticker that refreshes timer and every 5s refreshes history + one-line `sync_text`. There is no per-request trace and no manual trigger — close-flush (30s) is the only force-submit. SQLite access is serialized via `store._LOCK`; Flet updates must occur on the page event loop (`page.run_task` ticker), not from worker threads.

## Goals / Non-Goals

**Goals:**
- Brand-matched header debug entry opening a third debug view/sheet.
- Manual screenshot (queue + immediate upload), per-type sends, connection ping — all reusing existing `drain`/ack code paths.
- Live log of last 200 API calls: compact row + tap-to-expand truncated payload/response, token never shown.
- Copy debug bundle + Clear, usable for bug reports.

**Non-Goals:**
- No persistent `api_calls` table / migration; log is session-only.
- No backend contract change, no new dependencies, no auto-retry policy change.
- No employee-facing analytics; this is a dev-debug surface.

## Decisions

**1. Event bus: subscriber callback + thread-safe deque (over logging module or DB).**
`api.py:_post_json` / `post_screenshot` accept an optional `emit(fn)` hook; `sync.drain` threads the hook through. UI subscribes at startup and appends `ApiEvent{ts, method, path, item_count, status, accepted, error, req_preview, res_preview}` to `collections.deque(maxlen=200)`. Rationale: zero schema change, works for both scheduled and manual drains, testable by passing a fake emit. Alternative (parse `sync_runs` ledger) rejected — ledger has no per-call granularity.

**2. Manual actions reuse `sync.drain(reason="manual", tables=[...])` (over one-off POST code).**
Per-type filter (`sessions|activities|screenshots|all`) short-circuits unwanted `_drain_json` stages but keeps chunking (100/batch), ack-only marking, `note_error`, ledger write; with empty `api_base` the manual run logs a skipped `ApiEvent` and returns. Screenshot button resolves target session as active `state["sid"]` when recording else `MAX(sessions.id)` via `store.list_sessions(con, 1)`, refusing with a Launch-first hint when none exists; then `shots.take() → store.add_screenshot(target_sid)` followed by a screenshots-stage drain. Test ping tries `GET {base}/health` first, falls back to empty `POST /v1/sessions` probe on 404/network path errors, and never marks rows uploaded. Rationale: identical semantics to prod, no divergent upload path.

**3. Flet rendering via existing ticker poll (over direct `page.update()` from workers).**
Worker threads only append to deque; ticker (1s) drains new events into `ListView` controls every tick when debug view is visible. Expandable rows use `ExpansionTile`-style controls with pre-truncated previews (2KB req / 1KB res, `...truncated` suffix). Rationale: Flet 1.x requires UI mutation on page loop; avoids cross-thread crashes already guarded in `refresh_history`.

**4. Third view pattern mirroring settings (over modal dialog — confirmed full view per user 2026-10-02).**
`debug_view: Column(visible=False)` toggled like `settings_view`; header gets a bug-icon `IconButton` styled with `brand.MOON_WHITE` to match gear/theme buttons. Actions row + log `ListView(expand=True)` + footer `[Copy][Clear]`. Manual buttons run `threading.Thread(drain)` so UI never blocks; UI-level busy guard disables manual buttons while a manual run is in flight (scheduled 10-min tick may still interleave — harmless via idempotent `client_id` + `uploaded` flag). Rationale: reuses proven show/hide code, fits 340x560 window, scrollable.

**5. Redaction + truncation at emit site (over UI-side filtering).**
`api.py` builds previews from already-serialized items with `api_token`/`Authorization` stripped; bodies over limit are cut with byte counts. Copy bundle composes `version + pending_counts + last_sync + last 20 events` via `page.set_clipboard`. Rationale: secret can never reach the deque even if UI is screenshared.

## Risks / Trade-offs

- [Risk] Log deque grows with screenshots metadata (paths) → Mitigation: screenshots log meta only (filename + KB), never image bytes; 200-cap bounds memory.
- [Risk] Manual drain races scheduled tick (double POST same chunk) → Mitigation: existing ack-idempotent `client_id` + `uploaded` flag make double-send harmless; document that manual + tick may interleave.
- [Risk] Flet `ListView` with 200 expandable rows janks on low-end → Mitigation: render newest-first, cap visible to 60 with "show more"; previews pre-truncated.
- [Risk] Debug surface confuses non-technical staff → Mitigation: compact labels + tooltips; no destructive actions (Clear affects log only, never outbox).
- [Risk] Ping endpoint may not exist on proprietary backend → Mitigation: fall back to empty sessions probe; any HTTP response (even 4xx) counts as "reachable, see status".
