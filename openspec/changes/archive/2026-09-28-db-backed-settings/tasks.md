## 1. Settings storage

- [x] 1.1 Add `settings(key TEXT PRIMARY KEY, value TEXT)` to `SCHEMA` plus `get_setting` / `set_setting` (trim, allowlist `api_base|api_token|user_id`, immediate commit) / `get_settings_dict` in `store.py`
- [x] 1.2 Add store tests: table auto-creates on old DB, round-trip with trimming, missing key reads `""`, unknown key rejected
- [x] 1.3 Switch `sync._drain` and `app.start_background_threads` to read the 3 keys from the DB each cycle (no cached `cfg` for these keys); keep intervals on `cfg`

## 2. Settings screen

- [x] 2.1 Add home↔settings view swap with gear icon, Back action, and `refresh_settings()` repopulating fields from DB on every entry
- [x] 2.2 Add `api_base` / `user_id` fields with strict validation (http(s) URL, non-empty trimmed), per-field errors, trimmed save with success confirmation
- [x] 2.3 Add masked `api_token` field (`password=True`, no reveal), locked after save until Change clears to empty input; Change-save overwrites, empty rejected
- [x] 2.4 Add persistent "settings incomplete" hint on home until all 3 keys validate

## 3. Start gating and docs

- [x] 3.1 Gate Flet `on_start` on valid settings: refuse with guidance to settings, no session row created
- [x] 3.2 Update README (DB as source of truth for 3 keys, TOML keys inert, deleting `tracker.db` resets settings) and verify `pytest` + manual Flet smoke (open, save, Start, Back)
