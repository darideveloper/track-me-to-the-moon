## Why

Identity and API settings (`api_base`, `api_token`, `user_id`) currently live in `config.toml` with no UI — users must hand-edit a dotfile. This change makes them first-class: stored as a DB singleton, editable from a gear-icon settings screen, with the API token masked and strict validation so uploads are never sent with a half-configured identity.

## What Changes

- Add a `settings(key TEXT PRIMARY KEY, value TEXT)` table in `tracker.db` holding exactly `api_base`, `api_token`, `user_id` (clean break: existing `config.toml` values are NOT imported; users re-enter once).
- Add `store.get_setting` / `store.set_setting` / `store.get_settings_dict` helpers; background workers and uploader re-query the DB instead of holding a stale in-memory `cfg` dict for these keys.
- Add a settings view in the Flet UI reachable from a top-left gear icon on the home screen, with Save/Back, strict validation (`api_base` must be `http(s)` URL, `user_id` non-empty, token non-empty), and token UX: masked `••••` after save, editable only after an explicit Change action.
- Gate tracking Start on valid settings (Start blocked with guidance until the 3 keys validate).
- **BREAKING**: `config.toml` is no longer the source of truth for these 3 keys; deleting `tracker.db` now also resets identity/API settings. Timing intervals stay in `config.toml` (out of scope).

## Capabilities

### New Capabilities
- `settings-storage`: DB-singleton persistence and accessors for the 3 identity/API keys.
- `settings-screen`: gear-icon settings view with validation, masked-token + Change flow, Save/Back.

### Modified Capabilities
- `flet-ui`: home view gains a gear-icon entry point to settings; Start is gated on valid settings.

## Impact

- `src/worktracker/store.py` (new table + helpers + tests), `src/worktracker/ui.py` (views, nav, validation), `src/worktracker/sync.py` + `src/worktracker/app.py` (read settings from DB per cycle, not cached dict).
- `config.py` DEFAULTS drops the 3 identity keys (leftover copies in old files are loaded but never read); intervals unchanged, docs updated.
- No new dependencies; tray frontend stays Flet-only for settings (no pystray changes).
- Security posture unchanged at rest (plaintext in SQLite, same as TOML); masking is anti-shoulder-surfing only — OS keyring deferred.
