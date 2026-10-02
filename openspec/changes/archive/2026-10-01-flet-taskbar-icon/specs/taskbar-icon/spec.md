## ADDED Requirements

### Requirement: Linux X11 taskbar icon

The system SHALL, on Linux, copy `assets/moon-icon-256.png` over the resolved Flet desktop client's `data/app_icon.png` before `ft.run`, so the client's `gtk_window_set_default_icon` renders the moon icon. Resolution MUST go through `flet_desktop.ensure_client_cached()` (no hardcoded client version or flavor). The step is best-effort and SHALL never prevent the window from opening.

#### Scenario: X11 taskbar shows the moon

- **WHEN** the app launches on Linux with a resolvable Flet client cache
- **THEN** the client's `data/app_icon.png` equals the moon asset and the taskbar entry shows the moon icon

#### Scenario: Unresolvable client never blocks startup

- **WHEN** the client cache or its `data/` directory cannot be located or written
- **THEN** the app starts normally with the previous icon

### Requirement: Linux desktop identity with auto-installed entry

The system SHALL, on Linux GUI launches, set `FLET_APP_ID=moon-tracker` before `ft.run` and auto-install a matching user-scope desktop entry plus icon: `~/.local/share/applications/moon-tracker.desktop` (`Name=Track Me to the Moon`, `Exec` pointing at the repo `run.sh`, `Path` the repo root, `Icon=moon-tracker`, `StartupWMClass=moon-tracker`) and `~/.local/share/icons/hicolor/256x256/apps/moon-tracker.png`, followed by best-effort `update-desktop-database` and `gtk-update-icon-cache` runs. Installation is idempotent, skipped in CLI modes (`--once`, `--shot`, `--version`), suppressed by `MOON_TRACKER_NO_DESKTOP_ENTRY=1`, and SHALL never prevent the window from opening. Known limitation (verified against flet-desktop-light-1.0.1): the prebuilt client pins its WM_CLASS/app id, so `FLET_APP_ID` names the process but the entry matches the app-menu launcher, not the running window; a Wayland running-window icon requires a packaged build.

#### Scenario: App-menu launcher shows the moon

- **WHEN** the app has launched once on Linux with the entry installed
- **THEN** the desktop app menu shows a "Track Me to the Moon" launcher with the moon icon that starts the tracker

#### Scenario: Rerun is a no-op

- **WHEN** the app launches with identical entry and icon content already installed
- **THEN** the installed files are byte-identical and startup proceeds normally

#### Scenario: Opt-out suppresses installation

- **WHEN** `MOON_TRACKER_NO_DESKTOP_ENTRY=1` is set
- **THEN** no desktop entry or icon is written

#### Scenario: Missing refresh tools do not fail

- **WHEN** `update-desktop-database` or `gtk-update-icon-cache` is unavailable
- **THEN** installation is still considered successful and the app starts

### Requirement: Windows window icon

The system SHALL pass `assets/moon-icon.ico` (not the PNG) to `page.window.icon` on Windows.

#### Scenario: Windows window uses the .ico

- **WHEN** the app launches on Windows
- **THEN** the window titlebar/taskbar button uses the moon `.ico`

### Requirement: macOS dock icon (best-effort)

The system SHALL attempt, on macOS, to replace the recognized icon resource inside the cached Flet client `.app` bundle with the moon `.icns` before `ft.run`; if the bundle layout is unrecognized the step is skipped silently. The step SHALL never prevent the window from opening.

#### Scenario: Recognized bundle gets the moon

- **WHEN** the app launches on macOS and the cached bundle contains the expected icon resource
- **THEN** the Dock shows the moon icon

#### Scenario: Unrecognized bundle never blocks startup

- **WHEN** the cached bundle layout is not recognized
- **THEN** the app starts normally with the previous icon
