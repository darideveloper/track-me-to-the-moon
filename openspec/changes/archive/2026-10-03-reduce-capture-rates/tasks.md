## 1. Config defaults + existing-install migration

- [x] 1.1 Update `DEFAULTS` in `src/moon_tracker/config.py` to `poll_interval_sec = 360`, `screenshot_interval_sec = 900` (`idle_after_sec = 180` unchanged)
- [x] 1.2 Add old-default migration in `config.load()`: rewrite `5 → 360` and `300 → 900` only on exact match, persist file, leave custom values untouched
- [x] 1.3 Handle corrupt/missing file paths (keep ponytail fallback to defaults; ensure new file writes new defaults)

## 2. Screenshot jitter

- [x] 2.1 Change jitter in `src/moon_tracker/app.py` workers loop from `random.uniform(0, 30)` to `random.uniform(0, 120)`
- [x] 2.2 Keep `last_shot` update on capture failure (no busy-retry), verify `stop.wait()` still wakes on `stop.set()`

## 3. Docs

- [x] 3.1 Update `README.md` header line (`every 5s` / `every 5-10 min` → `every 6 min` / `every ~15 min`) and `Config keys` block to `360` / `900`
- [x] 3.2 Add one-line footnote in `README.md` about coarse idle granularity (6-min buckets) and the old-default auto-migration rule

## 4. Tests

- [x] 4.1 Add `tests/test_capture_intervals.py`: fresh `load()` writes 360/900; old-default file migrates; custom values preserved
- [x] 4.2 Run `uv run --frozen --extra dev pytest` (or `uv sync --frozen --extra dev` first) and fix regressions

## 5. Rollout on current system (your machine)

- [x] 5.1 `git pull --ff-only`, restart tracker via `run.sh`/`run.bat`, confirm `~/.config/moon-tracker/config.toml` now shows `360`/`900`
- [x] 5.2 If your `config.toml` had custom values, verify they were NOT overwritten; hand-edit to `360`/`900` if you still want sparse rates
- [x] 5.3 Smoke check: `python -m moon_tracker --once` still polls; run 20 min, query `tracker.db` (`SELECT COUNT(*) FROM activities/screenshots`) to confirm sparse rows; check `shots/YYYY-MM-DD/` for ~1 shot
- [x] 5.4 Confirm background `sync` still drains (debug panel → Send all) with no errors at low volume
