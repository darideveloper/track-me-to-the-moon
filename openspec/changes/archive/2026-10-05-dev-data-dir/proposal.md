## Why

Developing while tracking is unsafe today: every run resolves to the single `~/.local/share/moon-tracker/tracker.db`, so a dev Launch force-ends the prod session (`store.py:100-104`), overwrites prod credentials, and mixes screenshots into one `shots/` folder. The user needs a prod instance recording all day plus a fully working dev instance (own `api_base`/`user_id`/`api_token`, own uploads) side by side, with an unmissable indicator of which window is dev.

## What Changes

- Add `--data-dir <path>` CLI flag plus `MOON_TRACKER_DATA_DIR` env fallback (precedence: flag > env > default) that replaces the resolved data dir (`tracker.db` + `shots/`) for that process. `config.toml` (intervals) stays global.
- Resolve relative paths against cwd, normalize to absolute, create dir + `shots/` on start, print `data dir: <abs>` on startup.
- Per-dir identity for free: each `tracker.db` holds its own `api_base`/`api_token`/`user_id` via the existing settings screen; dev starts empty and remembers after first Save.
- Dev-mode UI badge (only when resolved dir != default): Flet window title suffix `[🧪 <label>]`, version footer extended with `· <abs path>`, tray title suffix; full absolute path shown in the footer.
- Skip OS launcher rewrite (`moon-tracker.desktop` + client icon patch) when non-default so dev never hijacks the prod menu entry.
- Thread the resolved dir through all 5 `config.data_dir()` call sites (`ui.py:77`, `app.py:31,116,200`, `sync.py:307`) instead of re-calling the global.
- Ignore `dev-data/` in `.gitignore`; document `./run.sh --data-dir dev-data` flow in README.
- No schema change, no profiles, no lockfile, no config split.

## Capabilities

### New Capabilities

- `dev-data-dir`: isolated data directory selection (`--data-dir` + env), per-dir DB/shots/settings, non-default UI badge (Flet title + footer, tray title), launcher-write skip, `dev-data/` git-ignored.

### Modified Capabilities

- `flet-ui`: window title and version footer gain a dev suffix when running on a non-default data dir.
- `portable-launchers`: launchers forward `--data-dir` to the app (`run.sh` already passes `$@`; ensure `run.bat` parity) and document the dev flow.

## Impact

- Code: `config.py` (override-aware `data_dir()`, `default_data_dir()`, `is_default_dir()`, `short_label()`), `app.py` (argparse, threading, tray suffix, startup log), `ui.py` (closure-injected dir, title/footer badge), `sync.py` + `shots` call sites (explicit dir param), `brand.py` (tray suffix helper), `run.bat`, `.gitignore`, `README.md`.
- Behavior: default runs byte-identical to today (no badge, same paths). Non-default runs fully isolated except shared `config.toml` intervals.
- Tests: existing `tmp_path`/`XDG_*` suite unaffected; new tests for precedence, isolation, and badge helpers.
- Ops: two Flet/tray processes can run concurrently (different files, no shared lock contention); both capture the same physical screen — expected, dev uploads to its own backend.
