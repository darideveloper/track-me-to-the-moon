## Why

The tracker shipped with the generic `worktracker` name, default Flet styling, and a green/grey square tray icon — no identity, and a Start/Stop UI indistinguishable from any demo app. Rebranding to **Track Me to the Moon** gives the product a memorable identity (moon-as-launch-control metaphor), a coherent dark/light visual system, and a single branded installable (`moon-tracker`) while preserving all existing user data through automatic migration.

## What Changes

- Product display name is **Track Me to the Moon** in the window title, tray titles, toast notifications, and package description; Python package renamed `worktracker` → `moon_tracker`, distribution renamed to `moon-tracker`.
- **BREAKING**: `python -m worktracker` no longer resolves; use `python -m moon_tracker` (a `worktracker` console-script alias is kept for compatibility). Config/data dirs move `~/.config/worktracker` → `~/.config/moon-tracker` (and `~/.local/share/...` likewise), with one-way auto-migration of legacy dirs on first start.
- Night-sky header (fixed deep-navy brand anchor in both themes) with moon-phase glyph, monospace timer, recording status, and sync line.
- Eclipse toggle (C×D) replaces the Start/Stop button pair: a 280px pill track with a sliding moon knob, captions **Tap to Launch / Tap to Land** (Start/Stop kept as tooltips); tray menu relabeled **Launch / Land**.
- Lunar Minimal dark theme + Paper Moon light theme via `page.theme`/`page.dark_theme`, `ThemeMode.SYSTEM` default with a manual dark/light override button.
- C×E coherence: header moon, toggle knob, tray icon (moon asset + sky ring when recording), and history-row leading dots all read one shared helper module (`brand.py`); sync states render as 🌘 pending / 🌕 synced.
- Geometric moon icon asset (`assets/moon-icon.png`, plus 256px and `.ico`) wired into the tray icon, Flet window icon, and PyInstaller `--icon` build flag.
- Operate-pass polish: history empty state ("tap the moon to launch 🚀"), settings fields wrapped in a `Card`, per-session upload dots (`list_sessions` now also returns `uploaded`).

## Capabilities

### New Capabilities
- `moon-branding`: Display name, Lunar Minimal + Paper Moon theme tokens, night-sky header, eclipse toggle control, moon icon assets, and the shared recording/sync glyph language across window, tray, and history.
- `module-rename`: `moon_tracker` package and `moon-tracker` distribution/entry points, `moon-tracker` config/data directories, and one-way auto-migration of legacy `worktracker` directories.

### Modified Capabilities
- `flet-ui`: Start/Stop button pair replaced by the eclipse toggle (Launch/Land copy, invalid-state handling unchanged: toggle to Launch with invalid settings redirects to settings); history rows gain moon-phase leading dots and an empty state; settings view gains Card container; window grows to 340×560 with title and icon.

## Impact

- Affected code: new `src/moon_tracker/brand.py`, rewritten `ui.py` header/toggle/history/settings sections, `app.py` (tray titles, menu labels, asset-backed `_icon`), `store.list_sessions` (+`uploaded` column), `config.py` (dir rename + `_migrate_dir`), `notify.py`/`sync.py` (branded strings), `pyproject.toml` (dist name + scripts), `tools/build.sh` (`--icon`, `--name`), `README.md`, new `assets/moon-icon.*`.
- No new runtime dependencies (Pillow already required; Flet theming uses built-in `Theme`/`ThemeMode` APIs).
- User data: existing sessions/settings/screenshots preserved via automatic directory migration; deleting `tracker.db` still resets settings as before.
