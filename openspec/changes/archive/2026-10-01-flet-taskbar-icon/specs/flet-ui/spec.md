## MODIFIED Requirements

### Requirement: Small resizable window

The system SHALL open a desktop window titled "Track Me to the Moon" defaulting to approximately 340x560 pixels that is freely resizable, showing the branded window icon and platform taskbar/dock identity when available (see `taskbar-icon`), with the history area scrolling when content overflows.

#### Scenario: Default size and resize

- **WHEN** the app launches
- **THEN** the window is approximately 340x560 with the branded title; and WHEN the user drags the window edge, the layout reflows and the history list scrolls instead of clipping

#### Scenario: Branded taskbar identity

- **WHEN** the app launches
- **THEN** the window titlebar and the platform taskbar/dock entry use the branded moon identity when available
