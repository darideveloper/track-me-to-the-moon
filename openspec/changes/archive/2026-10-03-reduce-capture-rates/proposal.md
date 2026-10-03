## Why

Current defaults record ~720 activity rows/hour (every 5s) and ~11-12 screenshots/hour (every 5-5.5 min). This is too chatty for the team's privacy, disk, bandwidth, and backend-cost goals. We want sparse, predictable sampling: 10 activities/hour and 4 screenshots/hour, applied globally so every new user/install gets it by default.

## What Changes

- Change default `poll_interval_sec` from `5` to `360` (10 activities/hour while running).
- Change default `screenshot_interval_sec` from `300` to `900` (4 screenshots/hour while active).
- Scale screenshot jitter from `+0-30s` to `+0-120s` so 15-min shots are not wall-clock predictable.
- Update `README.md` intervals (`5s` / `5-10 min` → `6 min` / `15 min`) and `Config keys` block.
- Migrate existing installs: if `config.toml` still holds old defaults (`5` / `300`), rewrite to new defaults; preserve any user-customized values.
- No schema changes; no sync-protocol changes; screenshots remain primary-monitor JPEG `~1280px/q60`.

## Capabilities

### New Capabilities

- `capture-intervals`: capture cadence requirements — activity poll rate, screenshot rate, jitter, idle interaction, and first-run vs. existing-install defaults.

### Modified Capabilities

(none — no existing `openspec/specs/` requirements cover capture cadence)

## Impact

- Affected code: `src/moon_tracker/config.py` (DEFAULTS + migration), `src/moon_tracker/app.py` (jitter window), `README.md` (docs).
- Behavior: idle granularity becomes coarse (6-min buckets vs. 5s); app-switches shorter than 6 min may be missed — accepted tradeoff for sparse sampling.
- Existing installs: one-time config migration on `config.load()`; no DB migration; unsent outbox rows keep old density.
- Rollout: new installs get new rates automatically (no `config.toml` → defaults written); existing installs updated on next `git pull` + restart.
