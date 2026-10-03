## Context

`app.start_background_threads()` (`src/moon_tracker/app.py:17-42`) runs a single loop: `stop.wait(poll_interval_sec)` → `collect.poll()` → `store.add_activity(...)` → maybe `shots.take()` if `time - last_shot >= screenshot_interval_sec + random(0,30)` and not idle. Defaults live in `config.DEFAULTS` (`src/moon_tracker/config.py:10-14`) and are written to `config.toml` on first run by `config.load()`; existing files override defaults. `sync.py` drains every 10 min regardless of cadence. No tests assert interval values.

Stakeholders: employees (privacy), admins (backend cost), support (existing installs with old `config.toml`).

## Goals / Non-Goals

**Goals:**
- 10 activities/hour (360s) and 4 screenshots/hour (900s) for all new installs with zero manual steps.
- Existing installs converge to new rates on next update+restart unless the user explicitly customized intervals.
- Keep change to config + one jitter constant + docs; no schema, sync, or UI changes.

**Non-Goals:**
- Accurate per-minute app timelines or precise idle accounting (explicitly traded away).
- Server-side downsampling or local aggregation (fast-poll/sparse-store) — rejected as over-engineering for this goal.
- Exposing intervals in the Flet settings screen.
- Backfilling or deleting already-recorded high-density rows.

## Decisions

1. **Naive interval bump over aggregate-then-store.**
   - Why: user asked to "reduce all of that" (collection, not just upload). Bump is 2 constants + migration; aggregation keeps 5s wakeups/CPU and needs summarization rules (mode vs. last vs. split) with no consumer for them.
   - Alternative rejected: keep 5s poll, store 1/36th (preserves idle precision) — more code, same DB win, but no CPU/privacy win and new failure modes.

2. **Migrate old defaults, preserve custom values.**
   - Why: changing `DEFAULTS` alone leaves every existing `config.toml` (with `5`/`300` baked in) on old rates — the "global" requirement fails for the current fleet.
   - Rule in `config.load()`: after loading file, if `poll_interval_sec == 5` → set `360`; if `screenshot_interval_sec == 300` → set `900`; persist rewritten file. Any other value (user-tuned) is left untouched.
   - Alternative rejected: grandfather (do nothing) — simplest but violates "update it in my current system"; force-overwrite — destroys intentional customization.

3. **Scale jitter 30s → 120s on screenshots.**
   - Why: at 900s cadence, 0-30s is ~3% and shots land near wall-clock :00/:15/:30/:45 (posing risk). 0-120s (~13%) matches the prior ~10% ratio and keeps Apploye-like unpredictability.
   - Keep `last_shot = time.time()` update even when `shots.take()` returns None (as today) so failures don't busy-retry.

4. **Docs-only surface change.**
   - `README.md` header ("every 5s / every 5-10 min") and `Config keys` block updated to 360/900. No settings-screen or debug-panel changes.

## Risks / Trade-offs

- [Risk] 6-min sampling misses short app switches; idle onset/offset error up to ±6 min → Mitigation: documented as accepted; `idle_after_sec=180` unchanged so flags remain conservative (idle still recorded, just late).
- [Risk] User who intentionally set `5`/`300` gets silently migrated → Mitigation: only exact old-default values migrate; anyone who edited to anything else is untouched. Note in release message.
- [Risk] Long `stop.wait(360)` delays shutdown reaction by up to 6 min for the worker thread → Mitigation: `threading.Event.wait` already wakes on `stop.set()`; shutdown path unaffected. Verify in test.
- [Risk] Screenshot timer drift if machine sleeps → Mitigation: `time.time()` wall-clock as today; no monotonic change needed at this cadence.

## Migration Plan

- Deploy: merge change; users `git pull --ff-only` + restart (`run.sh`/`run.bat`). No DB migration.
- New installs: `config.toml` created with 360/900 automatically.
- Existing installs: first `config.load()` after update rewrites old defaults → new defaults, preserves all other keys/values.
- Rollback: revert constants; already-migrated files keep new values (user can edit `config.toml` back) — no data loss either direction.
