## MODIFIED Requirements

### Requirement: Moon icon assets

The system SHALL ship a geometric crescent-on-disc moon icon (`assets/moon-icon.png` plus 256px, `.ico`, and `.icns` variants) used for the tray icon (with a sky ring overlay while recording), the per-platform taskbar/dock identity (Flet window icon via `.ico` on Windows; cached-client icon patch plus `FLET_APP_ID` and an auto-installed `.desktop` entry on Linux; cached-bundle icon patch on macOS, best-effort), and the PyInstaller `--icon` build flag, with a drawn fallback if an asset is missing. All icon-identity work is best-effort and SHALL never prevent the window from opening.

#### Scenario: Recording tray shows the ring

- **WHEN** tracking starts
- **THEN** the tray icon is the moon asset with a sky-blue ring; and WHEN stopped, the plain moon asset

#### Scenario: Missing asset never breaks startup

- **WHEN** the icon file is absent or unreadable
- **THEN** the tray falls back to the legacy drawn icon and the window opens without an icon

#### Scenario: Linux taskbar shows the moon

- **WHEN** the app launches on Linux
- **THEN** the taskbar entry shows the moon asset on X11 (window icon) and the app menu shows the moon launcher; a Wayland running-window icon requires a packaged build
