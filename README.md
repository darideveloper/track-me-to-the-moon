# Track Me to the Moon (moon-tracker v1)

Simple team work tracker (Apploye-like): Start/Stop timer, active app + window title every 5s, JPEG screenshot every 5-10 min, offline SQLite queue, background upload to proprietary API.

Title-only (no browser URLs). X11 recommended on Linux (Wayland blocks global window info).

## Quickstart

```bash
pip install -e .
python -m moon_tracker --help
python -m moon_tracker --once        # one poll print, no UI
python -m moon_tracker               # Flet window: live timer, Launch/Land, last 10 sessions
```

## Portable run (no install, easy update)

Clone and double-click — no build step, tracks `main`:

```bash
git clone <repo-url> moon-tracker
cd moon-tracker
```

- Windows: double-click `run.bat`
- Linux: `./run.sh` (make executable once: `chmod +x run.sh`)

The launcher checks git + Python 3.10+, installs `uv` if missing
(`uv python install 3.12` fallback), syncs exact deps from `uv.lock`,
warns if you're not on `main`, then opens the tracker. Keep the
terminal open — logs show there.

First run downloads ~100MB (Flet/Flutter) — looks stuck, isn't.
Windows may show a firewall prompt for the tracker window; that's expected.
On Linux Wayland, window titles are best-effort (X11 recommended).

First-time setup: open the ⚙ settings screen and paste the
`api_base` / `user_id` / `api_token` sent via chat, then Save.
Settings live in `tracker.db`, so updates never wipe them.

Update anytime (seconds, data preserved):

```bash
git pull --ff-only
```

then re-run `run.bat` / `run.sh` (re-syncs deps automatically).
If the tree is dirty the pull aborts — commit or stash first.
No separate updater script. The footer shows your version
(`main@<hash> <date>`) — quote it in bug reports.

Diagnostics: `run.sh --once` (one poll, no UI), `run.sh --version`.

Contributors: `uv sync --frozen --extra dev` then `uv run --frozen --extra dev pytest` to run the test suite.

Config, data, and shots dirs are auto-created on first start.

- Linux: `~/.config/moon-tracker/config.toml`, `~/.local/share/moon-tracker/tracker.db`, shots under `~/.local/share/moon-tracker/shots/YYYY-MM-DD/` (legacy `worktracker` dirs auto-migrate on first start)
- macOS: same as Linux (`~/.config/...`, `~/.local/share/...`)
- Windows: `%USERPROFILE%\.config\moon-tracker\config.toml`, `%USERPROFILE%\.local\share\moon-tracker\tracker.db`, shots under `%USERPROFILE%\.local\share\moon-tracker\shots\YYYY-MM-DD\`

`$XDG_CONFIG_HOME` / `$XDG_DATA_HOME` ( `%XDG_CONFIG_HOME%` / `%XDG_DATA_HOME%` on Windows) override the defaults when set.

## Settings

Identity and API settings (`api_base`, `api_token`, `user_id`) live in the
database (`settings` table in `tracker.db`) and are edited from the ⚙
settings screen in the Flet window (Save validates: `api_base` must be an
`http(s)` URL, token and employee ID non-empty; tracking can't Start until
valid). The token shows as `••••` after save and changes only via Change.
Leftover copies of those keys in old `config.toml` files are ignored.
Deleting `tracker.db` resets settings. Timing intervals stay in `config.toml`.

## Config keys

```toml
screenshot_interval_sec = 300
poll_interval_sec = 5
idle_after_sec = 180
```

If no `api_base` is stored in settings, uploader just keeps queue (offline mode).

## Permissions

- macOS: allow Screen Recording + Accessibility on first run.
- Linux: needs X11 session + `python3-xlib` deps (auto via PyWinCtl). Wayland = best-effort.
- Windows: no special perms.

## Features in progress

Browser **domain** capture (active tab hostname only) is developed on the
`web-extension` branch, not on `main`. See
[`docs/browser-extension-urls.md`](docs/browser-extension-urls.md) for the
feature description, privacy model, and settings toggle.

## Package

```bash
bash tools/build.sh
```

## Legal

Employee monitoring tool. Show Start/Stop state, get consent before rollout.
