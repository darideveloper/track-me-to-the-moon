## ADDED Requirements

### Requirement: Version footer in tracker window

The system SHALL display the runtime version string as a small footer/status line in the Flet tracker window.

#### Scenario: Footer shows current version

- **WHEN** the user opens the tracker window inside the repo
- **THEN** a footer line shows the version string (e.g. `main@a1b2c3d 2026-09-29`) without altering timer, history, or settings behavior

#### Scenario: Footer degrades gracefully

- **WHEN** the version string is `unknown`
- **THEN** the footer shows `unknown` and all other UI functions work normally
