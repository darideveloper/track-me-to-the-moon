# worktracker v1

Simple team work tracker (Apploye-like): Start/Stop timer, active app + window title every 5s, JPEG screenshot every 5-10 min, offline SQLite queue, background upload to proprietary API.

Title-only (no browser URLs). X11 recommended on Linux (Wayland blocks global window info).

## Quickstart

```bash
pip install -e .
python -m worktracker --help
python -m worktracker --once        # one poll print, no UI
python -m worktracker               # Flet window: live timer, Start/Stop, last 10 sessions
```

Config: `~/.config/worktracker/config.toml` (auto-created with defaults).
Data: `~/.local/share/worktracker/tracker.db`, shots under `~/.local/share/worktracker/shots/`.

## Config keys

```toml
api_base = ""
api_token = ""
user_id = ""
screenshot_interval_sec = 300
poll_interval_sec = 5
idle_after_sec = 180
```

If `api_base` is empty, uploader just keeps queue (offline mode).

## Permissions

- macOS: allow Screen Recording + Accessibility on first run.
- Linux: needs X11 session + `python3-xlib` deps (auto via PyWinCtl). Wayland = best-effort.
- Windows: no special perms.

## Package

```bash
bash tools/build.sh
```

## Legal

Employee monitoring tool. Show Start/Stop state, get consent before rollout.
