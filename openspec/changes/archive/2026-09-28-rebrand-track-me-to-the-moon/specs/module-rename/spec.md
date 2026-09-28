## ADDED Requirements

### Requirement: Renamed package and distribution

The system SHALL be distributed as `moon-tracker` with Python package `moon_tracker`, exposing `moon-tracker` and `worktracker` (compatibility alias) console scripts and a `moon-tracker` argparse program name; `import worktracker` SHALL NOT resolve.

#### Scenario: New entry points work

- **WHEN** the user runs `moon-tracker --help` or `python -m moon_tracker --once`
- **THEN** the CLI responds with program name `moon-tracker` and normal behavior

#### Scenario: Compat alias works

- **WHEN** the user runs the legacy `worktracker` command
- **THEN** it invokes the same entrypoint as `moon-tracker`

### Requirement: Renamed config and data directories with migration

The system SHALL store config under a `moon-tracker` directory and data (database, screenshots) under a `moon-tracker` directory, one-way auto-migrating legacy `worktracker` directories on first use; migration failure SHALL NOT block startup.

#### Scenario: Legacy directories migrate

- **WHEN** legacy `worktracker` config/data dirs exist and the new `moon-tracker` dirs do not
- **THEN** on startup the legacy dirs are renamed to `moon-tracker`, preserving sessions, settings, and screenshots

#### Scenario: Migration failure is non-fatal

- **WHEN** the legacy directory cannot be moved
- **THEN** the app starts normally and the old directory is left untouched
