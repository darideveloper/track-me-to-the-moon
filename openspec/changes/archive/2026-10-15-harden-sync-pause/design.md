## Context

The pause control (`SyncControl` in `src/moon_tracker/sync.py:20-62`) shipped in `8efb77e`/`323f08d` with no spec and is currently a wait-gate only: `loop` consults it via `wait_for_drain()` (`sync.py:385-392`), but `drain()` itself takes no control argument and never re-checks. A live audit proved the consequences:

- Pause mid-run does not stop uploads: 300 queued activities, pause clicked at t=0.2 s into a run → all 300 uploaded, 200 of them after the click. Upper bound is `MAX_RUN_SEC` (120 s) / `MAX_CHUNKS_PER_RUN` (10) plus up to ~60 single screenshot POSTs.
- `ui.on_close` (`ui.py:617-630`) and `app._close_flush` (`app.py:71-77`) call `flush()` unconditionally, so closing while paused uploads everything anyway.
- `run_tray` builds `state` without `sync_control` (`app.py:125`), so `loop` mints a private unreachable instance (`sync.py:387`) — tray users cannot pause.
- `_maybe_cleanup()` is called only from `drain()` (`sync.py:231`), so a long pause stalls the 7-day retention pass promised by `sync-reliability`.
- A 600-iteration hammer test on the pause/resume boundary with `interval=0` produced 0 drains started while paused, so the wait-gate itself is sound — no extra locking is needed there.

Stakeholders: anyone using pause as "keep data local" (privacy/off-network). Constraints: no DB migration, no backend/API changes, no config format changes; `drain()` back-compat callers (`_drain`, tests) must keep working.

## Goals / Non-Goals

**Goals:**
- Pause stops new uploads promptly (chunk boundary) in scheduled and in-flight runs.
- Close/quit respects pause: skip the 30 s flush, report kept count.
- Tray reaches parity with the Flet UI (shared control, menu toggle, status).
- Retention cleanup runs on its own daily gate regardless of pause.
- Status text distinguishes paused from stalled/error in both frontends.
- Manual Debug sends stay an explicit override and are documented as such.

**Non-Goals:**
- Pausing local capture (collector keeps queueing; a "pause capture too" option is a separate product decision).
- Persisting pause across restarts (stays runtime-only, resets to enabled).
- Mid-POST abort of an HTTP request already sent.
- Outbox size cap while paused (separate product decision).
- Changing ack semantics, chunk sizes, cadence, retry classification, or notification throttling.

## Decisions

**1. Preempt at chunk boundaries, not mid-POST.**
Check `control.is_enabled()` at the top of each `_drain_json` chunk iteration (`sync.py:121`), in the screenshot single-row loop (`sync.py:208`), and once in `loop` before calling `drain`. An already-sent POST completes normally (its ack is applied; never discard acked work). Alternative — cancelling the in-flight HTTP request — was rejected: it wastes the request, complicates the `mark_uploaded`/ledger transaction, and buys at most one chunk (~one POST) of promptness.

**2. Thread the control explicitly: `drain(..., control: SyncControl | None = None)`.**
`None` (default) means unconstrained, preserving every existing caller (`_drain`, tests, `manual_send`, `manual_screenshot`, close `flush` when unpaused). `loop`, the Flet close path, and the tray close path pass the live instance. Alternative — module-global control — was rejected for testability (the existing unit tests construct isolated instances) and because tray/Flet must not share globals across data dirs.

**3. Close/quit honors pause.**
When `control.is_enabled()` is false at close, skip `flush()` entirely and show "Sync paused — N items kept for next start" (Flet `sync_text`/snack; tray console print mirroring `_close_flush`). Rationale: a pause user who then closes reasonably expects nothing to leave the machine; silently uploading on exit (current behavior) defeats the feature's only purpose. Alternative — always flush — is documented here as rejected.

**4. Manual Debug sends bypass pause deliberately.**
`manual_send` / `manual_screenshot` / `test_connection` call the drain path with `control=None`. Rationale: they are explicit per-click user intent ("Send now"), distinct from automatic uploads. The spec states this so the bypass reads as designed, not as a leak.

**5. Tray parity via shared instance.**
`run_tray` adds `"sync_control": sync.SyncControl()` to `state` (same as `ui.main`), adds Pause/Resume `pystray.MenuItem`s toggling it, and extends the title with a paused marker. No new threads; the existing `loop` picks the instance up through `state.get("sync_control")`.

**6. Cleanup gets its own daily-gated entry point.**
Extract the gate from `_maybe_cleanup` into `run_retention_cleanup_if_due(con)` (pure, testable, still daily-gated on `last_notify_cleanup`). Because `wait_for_drain()` never returns `True` while paused, a call placed only after a `True` return would still starve cleanup — so `loop` SHALL be restructured to run the daily-gate check periodically (bounded slices, e.g. ≤60 s) even while paused, instead of only inside `drain()`. The existing 0.2 s paused-poll is the natural slice point to hook the check alongside. Alternative — a second timer thread — was rejected as a new lifecycle to manage for a daily task.

**7. Paused-aware status.**
`refresh_sync_status` (Flet) and `_tray_title` gain a paused branch that wins over the pending/failed/synced text (e.g. `⏸ paused — N pending`). Small `brand` helper keeps the two frontends consistent. Paused wording stays visually distinct from the 4xx/auth-pause "Sync unauthorized — check settings" hint (different cause, different remedy); if both hold, both are shown, not merged.

## Risks / Trade-offs

- [Risk] Pause checked at boundaries still lets one in-flight POST finish after the click → Mitigation: document boundary semantics in the spec; the window is one POST, not one run.
- [Risk] Skipping close-flush while paused grows the outbox across restarts (retry-forever guarantee means no loss, but disk grows) → Mitigation: kept-count message makes it visible; cap is an explicit non-goal.
- [Risk] `drain(control=...)` default `None` lets future automatic callers forget to pass the control → Mitigation: spec scenario pins every automatic path; a test asserts `loop` passes it.
- [Risk] Tray menu toggle and Flet pill could diverge in wording → Mitigation: single `brand` string helper.
- [Risk] Retention cleanup running while paused deletes only acked >7-day rows (same predicate), so no new data-loss surface → Mitigation: existing `cleanup_screenshots` tests stay green; add paused-cleanup test.

## Migration Plan

No migration: no schema, config, or API changes. Deploy is code + tests. Rollback is a plain revert; rows stay `uploaded=0` either way and sync resumes on next tick.

## Open Questions

Resolved before apply: (1) close-while-paused skips the flush — confirmed (a "flush anyway?" prompt was rejected as a blocking dialog on the close path); (2) pause stays upload-only with capture continuing, runtime-only reset, and no outbox cap — confirmed (all deferred as explicit non-goals).
