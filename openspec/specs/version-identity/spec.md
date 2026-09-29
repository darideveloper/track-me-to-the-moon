## Requirements

### Requirement: Runtime version string

The system SHALL expose a version string of the form `<branch>@<short-hash> <date>` derived from git at runtime, falling back to `unknown` outside a git checkout.

#### Scenario: Version reflects current commit

- **WHEN** the app runs inside the repo on branch `main` at commit `a1b2c3d` committed `2026-09-29`
- **THEN** the version string is `main@a1b2c3d 2026-09-29`

#### Scenario: Fallback outside git

- **WHEN** `.git` is absent (e.g. copied folder)
- **THEN** the version string is `unknown` and the app still starts normally

### Requirement: CLI exposes version

The system SHALL support `python -m moon_tracker --version` printing the version string and exiting zero.

#### Scenario: Version flag prints and exits

- **WHEN** the user runs `python -m moon_tracker --version`
- **THEN** the version string prints to stdout and the process exits zero without opening the UI
