## Why

The tracker works on the dev machine but there is no portable way to run it on Windows and Linux without a freeze/build step. The project is still in rapid development with many pending features, so a heavy release process (PyInstaller ZIPs, auto-updater) would slow iteration — yet a teammate needs to start using it ASAP and update in seconds.

## What Changes

- Add `run.bat` (Windows) double-click launcher: checks git + Python >= 3.10, bootstraps `uv` if missing (`uv python install 3.12` fallback), runs `uv sync --frozen`, warns if the checkout is not on `main`, then `python -m moon_tracker`.
- Add `run.sh` (Linux) launcher with the same flow plus X11/Wayland session warning and `python3-xlib` hint.
- Commit `uv.lock` so `uv sync --frozen` is reproducible on teammate machines.
- Add version identity: footer/status line in Flet UI shows `main@<short-hash> <date>` via `git rev-parse`, with `unknown` fallback when git is absent.
- Update via `git pull --ff-only` + re-run launcher (no separate updater script); launcher auto-syncs deps when `pyproject.toml`/`uv.lock` changed.
- Update `README.md` with clone-and-run quickstart for both OSes, first-run expectations (Flet ~100MB download), firewall note, and paste-token-from-chat settings flow.
- No changes to tracking behavior, DB schema, sync protocol, or data locations (config/DB stay in home dir so `git pull` never wipes sessions).

## Capabilities

### New Capabilities

- `portable-launchers`: zero-freeze Windows + Linux launchers with environment bootstrap (git/python/uv checks), branch guard warning off-`main`, first-run messaging, re-sync of deps on each launch (repeat runs work offline once synced), and pull-to-update flow.
- `version-identity`: runtime version string (branch, short hash, commit date) exposed to the UI and `--version` flag, with graceful fallback outside a git checkout.

### Modified Capabilities

- `flet-ui`: add a version footer/status element showing the version-identity string (display-only, no behavior change to timer/history/settings).
