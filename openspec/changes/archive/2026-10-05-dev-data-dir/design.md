## Context

Today `config.data_dir()` takes no arguments and resolves to `$XDG_DATA_HOME or ~/.local/share` + `/moon-tracker` (`config.py:38-43`), with `config_path()` alongside (`config.py:33-36`). Five call sites use the bare global: Flet DB open (`ui.py:77`), tray DB open (`app.py:116`), screenshot targets (`app.py:31`, `sync.py:307`), one-shot (`app.py:200`). Settings (`api_base`/`api_token`/`user_id`) live in `tracker.db`, so splitting the DB splits identity with no schema change. Flet's `ft.run(main)` takes a bare `fn(page)`, so the dir must be smuggled via closure. The OS launcher rewrite (`desktop_entry.py:64-107`) and icon patch run on every Flet start.

## Goals / Non-Goals

**Goals:**
- Run prod (default dir) and dev (`--data-dir dev-data`) concurrently, each fully working (capture + upload to its own backend).
- One-line badge making dev unmistakable in Flet title + footer and tray title.
- Zero behavior change on default path; minimal diff (ponytail).

**Non-Goals:**
- No per-row `user_id` column, no multi-profile DB, no `--config` split, no lockfile/single-instance guard, no banner pill, no header recolor.

## Decisions

1. **Data-only override, config stays global.** `--data-dir` replaces only the data dir (DB + `shots/`). Intervals in `config.toml` stay shared. Alternative (full root incl. config) rejected: doubles the path concept for a need the user explicitly declined.
2. **Precedence flag > env > default.** `--data-dir` wins, else `MOON_TRACKER_DATA_DIR`, else `XDG_DATA_HOME`/default. Rationale: flag for explicit dev launches, env for scripts that can't pass args. Relative input resolved against cwd then `Path.resolve()` (macOS `/tmp` symlink safety) before default-comparison so the badge never false-negatives.
3. **Helpers in `config.py`: `default_data_dir()`, `data_dir(override=None)`, `is_default_dir(resolved)`, `short_label(resolved)`.** `data_dir()` keeps its zero-arg signature working (override defaults from env) to avoid churning tests; new code passes explicit values. `short_label` = last 2 path components for title, full absolute kept for footer/tooltip.
4. **Thread, don't re-read.** `start_background_threads(con, cfg, state, stop, data_dir)` and `sync.manual_screenshot(con, cfg, state, data_dir=...)` receive the resolved dir; internal `config.data_dir()` calls become params. This closes the cross-write trap where DB splits but screenshots still land in prod.
5. **Badge = title + footer (+ tray), computed once at startup.** `page.title = f"{DISPLAY_NAME} [🧪 {label}]"`, footer `f"{version} · {abs}"`, tray `brand.tray_title(..., suffix)`. No layout/container changes, no theme interplay. Banner pill rejected as extra layout to test.
6. **Skip launcher side-effects in dev.** When non-default, skip `ensure_installed()` + `patch_client_icon()` (Flet) — prod menu entry stays intact. Rationale: dev checkout must not steal the prod launcher; cost is one branch.
7. **`dev-data/` inside repo + git-ignored.** Matches user workflow (`./run.sh --data-dir dev-data` from repo root after `run.sh`'s `cd`). Document `git clean -fdx` risk in README.

## Risks / Trade-offs

- [Missed `data_dir()` call site reintroduces cross-write] → Mitigation: grep-verify all 5 sites + test asserting `manual_screenshot` and worker shot path honor the injected dir.
- [Symlink/relative aliasing defeats `is_default_dir`] → Mitigation: always `resolve()` both sides before compare; on doubt, show badge.
- [Two collectors capture the same screen] → Accepted: separate backends, user expects duplication; documented.
- [Shared `config.toml` intervals edited in dev affect prod] → Accepted per user choice; intervals are low-stakes.
- [`git clean -fdx` deletes `dev-data/`] → Mitigation: README warning; settings are 3 re-typable strings.
- [Flet closure plumbing for `ft.run(main)`] → Use `functools.partial`/closure `def _main(page): return main(page, data_dir)`; keep `main(page, data_dir=None)` backward-compatible for tests.
