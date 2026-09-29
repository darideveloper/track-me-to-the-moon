## Context

`moon-tracker` is a Python 3.10+ Flet desktop app (`src/moon_tracker/`, entry `python -m moon_tracker` → Flet window). Deps are pinned in `pyproject.toml` (`flet==1.0.1`, mss, Pillow, PyWinCtl, psutil, pystray, pynput, requests) but there is no `uv.lock`. Data lives outside the repo (`~/.config/moon-tracker/`, `~/.local/share/moon-tracker/` on Linux; `%USERPROFILE%` equivalents on Windows), so replacing/updating the code folder never wipes sessions. The only build path is `tools/build.sh` (raw PyInstaller onedir), which requires per-OS builds and is overkill during rapid iteration.

Stakeholders: the developer (ships daily on `main`) and one technical teammate on an unknown Windows PC (plus the dev's own Linux box). Repo is public, so cloning needs no auth. Settings (`api_base`, `api_token`, `user_id`) are DB-backed and entered once via the ⚙ screen — teammate pastes the token from chat.

## Goals / Non-Goals

**Goals:**
- Double-click run on Windows (`run.bat`) and Linux (`run.sh`) with zero freeze/build step.
- Self-checking bootstrap: friendly errors for missing git/Python, auto-install of `uv` if absent, `uv python install 3.12` fallback.
- Reproducible env via committed `uv.lock` + `uv sync --frozen`.
- Pull-to-update in seconds (`git pull --ff-only` + auto `uv sync`); data and token survive.
- Visible version (`branch@hash date`) in UI + CLI for bug reports.

**Non-Goals:**
- No PyInstaller / `flet pack` ZIPs in this change (deferred to a later portable-freeze change).
- No auto-updater, no installer (MSI/AppImage), no Docker.
- No silent/autostart service — terminal stays open by design for log visibility.
- No `web-extension` branch support — launchers pin `main`.
- No DB migration or sync-protocol changes.

## Decisions

- **uv over system pip (`uv sync --frozen`).** Why: deterministic lockfile, fast re-sync, `uv python` can provision 3.12 when the teammate has an old Store Python. Alternative (pip + venv + `pip install -e .`) rejected: non-deterministic, slower, more support burden. Trade-off: first run downloads uv + ~100MB Flet wheels once.
- **Plain Batch (`run.bat`) over PowerShell script.** Why: double-click runs without execution-policy prompts; every Windows runs `.bat`. Keep it dependency-free (`where`, `py`, `powershell` only as downloader for uv). Alternative (PS1) rejected for the policy friction on unknown machines.
- **POSIX `run.sh` (bash, `set -euo pipefail`).** Why: matches existing `tools/build.sh` style, works on Debian/Ubuntu/Fedora. Uses `curl` with `wget` fallback for uv install.
- **Commit `uv.lock` generated from `pyproject.toml`.** Why: `--frozen` guarantees teammate resolves exactly `flet==1.0.1` etc. Regenerate lock whenever deps change; launcher never upgrades implicitly.
- **Version via `src/moon_tracker/version.py` reading git at runtime.** Why: single helper used by UI footer and `--version`; `git rev-parse --abbrev-ref HEAD`, `--short HEAD`, `%ci` date. Falls back to `unknown` (or embedded file if later frozen) when `.git` absent. Alternative (hardcoded `__version__`) rejected: drifts during daily pushes. No new dependency.
- **Launcher never switches branches or stashes.** `git pull --ff-only` only; dirty tree → print `git status --short` and stop with instructions. Prevents wiping teammate-local edits. Launchers check `git rev-parse --abbrev-ref HEAD` at startup and print a warning when the checkout is not on `main`, then continue (no auto-switch, no hard block).
- **No separate updater script.** Update = `git pull --ff-only` + re-run `run.bat`/`run.sh`, which re-runs `uv sync --frozen` automatically.
- **First-run messaging, not silence.** Echo download size warning (Flet ~100MB), firewall SmartScreen note, and Wayland/X11 warning on Linux. Reduces "it hung" support tickets.

## Risks / Trade-offs

- [Risk] Teammate has no git or Python → Mitigation: launcher stops early with exact download links (git-scm.com, python.org), exit code non-zero, no partial venv left behind.
- [Risk] First `uv sync` looks stuck (large Flet download) → Mitigation: explicit "first run downloads ~100MB, please wait" echo + `--frozen` progress passthrough.
- [Risk] Corporate AV flags `pynput`/`PyWinCtl` idle hooks → Mitigation: README documents the false-positive pattern and the `--once` smoke command to prove install without starting tracking.
- [Risk] Wayland session degrades window titles (known X11 limitation) → Mitigation: `run.sh` warns when `$XDG_SESSION_TYPE=wayland` but continues; titles are best-effort, timer/screenshots unaffected.
- [Risk] `git pull` conflicts with teammate-local edits → Mitigation: `--ff-only` + abort message; never auto-stash or reset.
- [Risk] `uv.lock` drift when `pyproject.toml` edited without re-lock → Mitigation: use `--frozen` in launchers and instruct dev to commit the lock with every dep change.
- [Risk] Windows firewall / SmartScreen prompt on first Flet launch alarms the teammate → Mitigation: README warns the prompt is expected and harmless; launcher prints the same note before starting the UI.
