## MODIFIED Requirements

### Requirement: Small resizable window

The system SHALL open a desktop window titled "Track Me to the Moon" defaulting to approximately 340x560 pixels that is freely resizable, showing the branded window icon and platform taskbar/dock identity when available (see `taskbar-icon`), with the history area scrolling when content overflows. WHEN running on a non-default data dir (see `dev-data-dir`), the title SHALL append a dev suffix `[🧪 <label>]` where `<label>` is the last two path components (full absolute path shown in the footer).

#### Scenario: Default size and resize

- **WHEN** the app launches
- **THEN** the window is approximately 340x560 with the branded title; and WHEN the user drags the window edge, the layout reflows and the history list scrolls instead of clipping

#### Scenario: Branded taskbar identity

- **WHEN** the app launches
- **THEN** the window titlebar and the platform taskbar/dock entry use the branded moon identity when available

#### Scenario: Dev title is labeled

- **WHEN** the app launches with `--data-dir dev-data`
- **THEN** the window title contains `[🧪` plus the short label while keeping the approximately 340x560 size and resize behavior

### Requirement: Version footer in tracker window

The system SHALL display the runtime version string as a small footer/status line in the Flet tracker window. WHEN running on a non-default data dir, the footer SHALL append `· <absolute data-dir path>`.

#### Scenario: Footer shows current version

- **WHEN** the user opens the tracker window inside the repo
- **THEN** a footer line shows the version string (e.g. `main@a1b2c3d 2026-09-29`) without altering timer, history, or settings behavior

#### Scenario: Footer degrades gracefully

- **WHEN** the version string is `unknown`
- **THEN** the footer shows `unknown` and all other UI functions work normally

#### Scenario: Dev footer shows data dir

- **WHEN** the user opens the tracker window with `--data-dir dev-data`
- **THEN** the footer line shows `<version> · <absolute path to dev-data>` without altering timer, history, or settings behavior
