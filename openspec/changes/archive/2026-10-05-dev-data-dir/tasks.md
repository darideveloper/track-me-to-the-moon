## 1. Config resolution

- [x] 1.1 Add `default_data_dir()`, `data_dir(override=None)` (flag > `MOON_TRACKER_DATA_DIR` > default, cwd-relative → absolute, mkdir `shots/`), `is_default_dir()`, `short_label()` in `src/moon_tracker/config.py` keeping zero-arg calls working.
- [x] 1.2 Add tests for precedence (flag > env > default), relative-to-absolute resolution, and default vs non-default detection.

## 2. Plumbing

- [x] 2.1 Add `--data-dir` to `app.py` argparse; resolve once at startup; print `data dir: <abs>`; pass to `store.connect()`, `shots.take()`, `ui.run()`, `--once`/`--shot`.
- [x] 2.2 Change `start_background_threads()` to accept `data_dir` and use it for worker shots (remove internal bare `config.data_dir()`).
- [x] 2.3 Change `sync.manual_screenshot()` to accept `data_dir` and use it (remove internal `_config.data_dir()`).
- [x] 2.4 Grep-verify no bare `config.data_dir()` remains on process paths; add test that worker + manual screenshot honor the injected dir.

## 3. Dev badge

- [x] 3.1 Inject `data_dir` into `ui.main(page, ...)` via closure for `ft.run`; append `[🧪 <label>]` to `page.title` and `· <abs>` to version footer only when non-default.
- [x] 3.2 Add tray title suffix helper in `brand.py` and thread through `app.py` tray title updates.
- [x] 3.3 Add tests for badge helpers (default = no suffix; dev = suffix with label/path).

## 4. Launcher + repo

- [x] 4.1 Skip `ensure_installed()` + `patch_client_icon()` when non-default in `ui.run()`.
- [x] 4.2 Verify `run.sh "$@"` forwards `--data-dir`; add same forwarding to `run.bat` if missing.
- [x] 4.3 Add `dev-data/` to `.gitignore`; extend debug `Copy bundle` with data-dir path; update README with `./run.sh --data-dir dev-data` + `git clean` warning.

## 5. Verify

- [x] 5.1 Run full suite `uv run --frozen --extra dev pytest`; manual smoke: `--data-dir dev-data --once` creates `dev-data/tracker.db`, prod untouched.
- [x] 5.2 Manual side-by-side: prod + dev Flets show distinct titles/footers; dev settings round-trip; `.desktop` untouched by dev launch.
