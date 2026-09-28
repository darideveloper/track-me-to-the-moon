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

Config, data, and shots dirs are auto-created on first start.

- Linux: `~/.config/worktracker/config.toml`, `~/.local/share/worktracker/tracker.db`, shots under `~/.local/share/worktracker/shots/YYYY-MM-DD/`
- macOS: same as Linux (`~/.config/...`, `~/.local/share/...`)
- Windows: `%USERPROFILE%\.config\worktracker\config.toml`, `%USERPROFILE%\.local\share\worktracker\tracker.db`, shots under `%USERPROFILE%\.local\share\worktracker\shots\YYYY-MM-DD\`

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

## Package

```bash
bash tools/build.sh
```

## Legal

Employee monitoring tool. Show Start/Stop state, get consent before rollout.
