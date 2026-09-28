## Context

Settings (`api_base`, `api_token`, `user_id`) live in `config.toml` (`config.py:load()`), loaded once into a `cfg` dict passed by reference to collector/uploader threads (`app.py:start_background_threads`, `sync.py:loop`). The Flet UI (`ui.py:main`) is a single static `Column` (timer → Start/Stop → history, 320×450) with no navigation. `store.py` owns `tracker.db` (sessions/activities/screenshots, WAL mode, `check_same_thread=False`) with no settings table. All explore gaps are closed: masked token + Change button, 3-keys-only scope, clean-break migration, KV table, Flet-only, strict validation, masking-only security.

## Goals / Non-Goals

**Goals:**
- Single source of truth for the 3 keys in `tracker.db`, readable/writable from UI and background threads without restarts.
- Gear-icon settings view with Save/Back, strict validation, and a token flow that survives typos and rotation.
- No stale-config bugs: threads always observe the latest saved values.

**Non-Goals:**
- Timing intervals stay in `config.toml` (not editable in UI).
- No tray settings UI; no OS-keyring encryption (deferred).
- No TOML import/migration tooling.

## Decisions

1. **KV table `settings(key PK, value TEXT)` over single-row** — mirrors the current `cfg` dict 1:1 (`SELECT key,value` → dict), so `sync.py`/`app.py` keep their access shape; adding a key later is an `INSERT`, not `ALTER TABLE`. Tradeoff: values are all TEXT (no typed columns) — acceptable for 3 strings.
2. **Clean break over import-once** — no TOML→DB copy; first launch shows empty settings and strict validation forces entry. Rationale: one-way import code is throwaway complexity with its own bug surface (partial copies, "which source won?"). Tradeoff: existing installs re-enter 3 values once.
3. **Re-query per cycle over cached dict + invalidation** — `sync.loop` (60s backoff) and the worker poll read settings fresh each iteration via a small helper. Rationale: invalidation is a second bug class; read volume is trivial. `store.connect` already uses WAL + short transactions, so contention is negligible.
4. **View swap over dialog** — home `Column` and settings `Column` toggle `visible`, plus Back. Rationale: 320×450 is too cramped for a 3-field dialog + validation messages; swap keeps layout code linear in the existing single-`page.add` style.
5. **Token UX: `TextField(password=True, can_reveal_password=False)`, locked after save until Change** — saved state renders `••••••••` (real value never placed in the control); Change clears to an empty editable input, Save overwrites. Rationale: standard masked + re-enterable covers typos and rotation; truly immutable was rejected in explore.
6. **Strict validation at Save (and Start gate)**: `api_base` must parse as `http(s)` URL, `api_token` and `user_id` must be non-empty after `strip()`. Values stored trimmed. Rationale: offline mode still queues data, but uploads with empty identity are silent poison — fail visibly at entry.
7. **Start gated on valid settings** — `on_start` refuses with inline guidance linking to settings when validation fails. Rationale: strict-at-Save alone still allows never-visiting-settings; gating closes the loop. Tray Start is ungated (Flet-only scope) and documented.

## Risks / Trade-offs

- [Risk] Deleting `tracker.db` now wipes identity/API settings (previously survived in TOML) → Mitigation: call out as **BREAKING** in proposal + README note; no code fix, accepted tradeoff of single-source.
- [Risk] Token at rest is plaintext in SQLite (same as TOML today); masking only stops shoulder-surfing → Mitigation: document posture explicitly; keyring tracked as follow-up, not this change.
- [Risk] Concurrent UI save vs. background read → Mitigation: each accessor is its own short transaction (`commit` immediately, as all existing `store.*` functions do); WAL mode already on.
- [Risk] Flet view-state drift (stale field values when returning to settings) → Mitigation: repopulate fields from DB on every navigation to settings, single `refresh_settings()` function.
- [Risk] Clean break strands existing `config.toml` users who never open settings → Mitigation: home shows persistent "Settings incomplete" hint until valid; Start gate points at the gear.

## Migration Plan

1. Deploy: `SCHEMA` gains `CREATE TABLE IF NOT EXISTS settings(...)`; existing DBs auto-migrate on next `connect()` with zero backfill (empty = incomplete → hint + gate).
2. TOML: `DEFAULTS` no longer contains the 3 keys, so new `config.toml` files hold intervals only; leftover keys in old files are loaded but never read (intervals still live there).
3. Rollback: revert code; the `settings` table stays as harmless dead data; TOML values remain on disk untouched (clean break never deletes them).
