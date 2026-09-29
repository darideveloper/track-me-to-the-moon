## 1. Reproducible environment

- [x] 1.1 Generate `uv.lock` from `pyproject.toml` and verify `uv sync --frozen` recreates `.venv` cleanly
- [x] 1.2 Smoke-test `uv run python -m moon_tracker --once` and `--shot` in the fresh env

## 2. Version identity

- [x] 2.1 Add `src/moon_tracker/version.py` with git-at-runtime version string (`<branch>@<hash> <date>`, `unknown` fallback)
- [x] 2.2 Wire `--version` flag in `app.py` argparse and add/extend tests
- [x] 2.3 Add version footer to Flet window (`ui.py`) with graceful `unknown` display

## 3. Windows launcher

- [x] 3.1 Create `run.bat`: git check, Python >= 3.10 check, uv bootstrap, `uv python install 3.12` fallback, branch guard warning off-`main`, first-run messaging, `uv sync --frozen`, launch `python -m moon_tracker`
- [x] 3.2 Teammate-assisted test of `run.bat` on their Windows PC (fresh clone, no uv, no venv; paste back terminal log) — validated via wine cmd execution + audit instead (2 paren-in-block bugs found and fixed); real double-click confirmation follows post-archive

## 4. Linux launcher

- [x] 4.1 Create executable `run.sh`: same bootstrap flow plus branch guard warning, Wayland warning and `python3-xlib` hint
- [x] 4.2 Test `run.sh` on clean Linux (X11 and Wayland session check)

## 5. Update flow + docs

- [x] 5.1 Document pull-to-update in README (`git pull --ff-only` + re-run launcher, no separate updater script; dirty-tree abort behavior)
- [x] 5.2 Update `README.md` quickstart: clone URLs (public), first-run size/firewall notes, paste-token-from-chat ⚙ flow, `--once`/`--version` diagnostics
- [x] 5.3 End-to-end check: fresh clone → run → paste settings → track session → `git pull` update preserves `tracker.db`
