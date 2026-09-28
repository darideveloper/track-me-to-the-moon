## Requirements

### Requirement: Product display name

The system SHALL present itself as "Track Me to the Moon" in the desktop window title, tray titles, toast notifications, and package description, while the Python package is `moon_tracker` (the display string is never used as an import name).

#### Scenario: Window title is branded

- **WHEN** the Flet window opens
- **THEN** the title bar reads "Track Me to the Moon"

#### Scenario: Tray and toasts are branded

- **WHEN** tracking state changes or a sync-failure toast fires
- **THEN** the tray title starts with "Track Me to the Moon" and notification titles use the display name (e.g. "Track Me to the Moon sync failed")

### Requirement: Lunar Minimal and Paper Moon themes

The system SHALL define a Lunar Minimal dark theme and a Paper Moon light theme sharing one sky-blue accent, applied via `page.theme` / `page.dark_theme`, defaulting to `ThemeMode.SYSTEM` with a manual override button cycling dark and light.

#### Scenario: System default is followed

- **WHEN** the app launches with no manual override
- **THEN** the body follows the OS light/dark setting

#### Scenario: Manual override works

- **WHEN** the user taps the theme button
- **THEN** the body switches to the opposite theme and the button icon updates to offer the way back

### Requirement: Night-sky header

The system SHALL render a fixed deep-navy header in both themes containing a moon-phase glyph, a monospace elapsed timer, recording status, a sync line, and a star row, with all glyphs pinned to explicit light colors so they stay visible in light mode.

#### Scenario: Header moon tracks recording

- **WHEN** tracking is stopped
- **THEN** the header shows a crescent (🌘); and WHEN recording starts, it shows a full moon (🌕) with a sky accent status dot

#### Scenario: Header moon visible in light mode

- **WHEN** the OS or override selects the light theme
- **THEN** the moon glyph, timer, status, and sync line remain legible against the dark header

#### Scenario: Sync line reflects ledger

- **WHEN** items are pending upload
- **THEN** the sync line shows "🌘 N pending"; and WHEN fully synced it shows "🌕 synced"; and WHEN the last run failed it shows the truncated error

### Requirement: Eclipse toggle control

The system SHALL provide a single pill-track toggle with a sliding moon knob (animated position) and a caption reading "Tap to Launch" when stopped and "Tap to Land" when recording, preserving the existing settings-gate (invalid settings redirect to the settings view without starting) and session create/close semantics.

#### Scenario: Launch creates a session

- **WHEN** settings are valid and the user taps the toggle while stopped
- **THEN** a new `sessions` row is created with `started_at` set and `ended_at` NULL, the knob slides to the recording end, and the caption becomes "Tap to Land"

#### Scenario: Land closes the session

- **WHEN** the user taps the toggle while recording
- **THEN** the current session row gets `ended_at` set and the knob slides back

#### Scenario: Launch refused with invalid settings

- **WHEN** the user taps the toggle while any of `api_base`, `api_token`, or `user_id` fails validation
- **THEN** no session row is created, recording does not start, and the UI directs the user to settings

### Requirement: Moon icon assets

The system SHALL ship a geometric crescent-on-disc moon icon (`assets/moon-icon.png` plus 256px and `.ico` variants) used for the tray icon (with a sky ring overlay while recording), the Flet window icon, and the PyInstaller `--icon` build flag, with a drawn fallback if the asset is missing.

#### Scenario: Recording tray shows the ring

- **WHEN** tracking starts
- **THEN** the tray icon is the moon asset with a sky-blue ring; and WHEN stopped, the plain moon asset

#### Scenario: Missing asset never breaks startup

- **WHEN** the icon file is absent or unreadable
- **THEN** the tray falls back to the legacy drawn icon and the window opens without an icon

### Requirement: Shared recording/sync glyph language

The system SHALL derive header moon, toggle knob, tray title suffix, and history-row dots from one shared helper module so all surfaces agree on recording and sync state.

#### Scenario: Surfaces agree on pending

- **WHEN** uploads are pending
- **THEN** the sync line, tray title, and unsynced history rows all show the pending (crescent) marker
