## Why

Opening the tracker shows the generic Flet logo in the taskbar instead of the moon icon (`ui.py:88` sets `page.window.icon`, which is Windows-only per Flet docs — a silent no-op on Linux and macOS). The moon-branding capability already promises a branded window icon; the taskbar/dock visibly contradicts that promise today.

## What Changes

- Give the Flet window a real per-platform taskbar/dock identity at startup:
  - **Linux X11**: copy `assets/moon-icon-256.png` over the cached Flet desktop client's `data/app_icon.png` before `ft.run` (this is the file the client feeds to `gtk_window_set_default_icon`), re-applied every launch.
  - **Linux (X11 + app menu)**: set `FLET_APP_ID=moon-tracker` and auto-install a matching user-scope `.desktop` entry plus hicolor icon (app-menu launcher with the moon; note: the prebuilt client pins its WM_CLASS, so a Wayland running-window icon needs a packaged build).
  - **Windows**: pass `assets/moon-icon.ico` to `page.window.icon` (currently passes a PNG where an `.ico` is required).
  - **macOS**: best-effort patch of the cached client `.app` bundle icon (needs macOS verification; packaging remains the robust route).
- Auto-install is idempotent, user-scope only (`~/.local/share`), skips CLI modes, honors `MOON_TRACKER_NO_DESKTOP_ENTRY=1`, and never breaks startup (icon work is decoration).
- One pytest for the pure helpers; README note covering what gets installed, how to remove it, and the permanent packaging path.

## Capabilities

### New Capabilities
- `taskbar-icon`: per-platform taskbar/dock identity for the Flet desktop window — Linux client-icon patch, `FLET_APP_ID` + `.desktop`/icon auto-install, Windows `.ico`, macOS `.icns` best-effort, opt-out, and verification.

### Modified Capabilities
- `moon-branding`: the "Moon icon assets" requirement's Flet-window-icon clause now means taskbar-visible identity per platform (X11 taskbar, app-menu launcher, Windows/macOS); the "never break startup" fallback is retained and extended to all new steps.
- `flet-ui`: the "Small resizable window" requirement's "shows the branded window icon" now includes taskbar/dock identity, not just the titlebar glyph.

## Impact

- `src/moon_tracker/ui.py` (startup path before `ft.run`, `page.window.icon` selection), new `src/moon_tracker/desktop_entry.py` (Linux helper), `tests/` (one helper test), README/docs note.
- No new runtime dependencies (`flet_desktop` is already a transitive dependency of `flet`); no changes to tracking, sync, or store behavior.
- User-visible side effects on Linux only: a `moon-tracker.desktop` entry and icon under `~/.local/share` (reversible, opt-out); on Flet upgrades the client patch is silently re-applied.
