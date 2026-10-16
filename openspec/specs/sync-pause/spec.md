## Requirements

### Requirement: Pause gate blocks automatic uploads

The system SHALL provide a runtime sync-pause gate that, while engaged, prevents the scheduled background loop from starting any new upload run and prevents an in-flight run from issuing new POSTs beyond the current chunk boundary.

#### Scenario: Scheduled tick skipped while paused

- **WHEN** the 10-minute timer fires while pause is engaged
- **THEN** the system issues no POSTs, leaves all rows `uploaded=0`, and schedules no retry beyond the next tick check

#### Scenario: In-flight run stops at the chunk boundary

- **WHEN** pause is engaged mid-run (300 activities pending, first 100-chunk POST in flight)
- **THEN** the in-flight POST completes and its ack is applied normally, but no further chunk or screenshot POST is issued and the remainder stays pending

#### Scenario: Local capture continues while paused

- **WHEN** tracking is running and pause is engaged
- **THEN** the collector keeps inserting activities and screenshots locally with no error and no upload

### Requirement: Resume triggers an immediate drain

The system SHALL, on transitioning from paused to enabled, start one drain run immediately rather than waiting for the next scheduled tick.

#### Scenario: Resume drains without waiting

- **WHEN** the user resumes with pending rows and the next tick is minutes away
- **THEN** the system starts a drain within ~1 second covering sessions, activities, and screenshots under the normal run budget

### Requirement: Pause is runtime-only and resets on start

The system SHALL initialize the pause gate to enabled on every app start and SHALL NOT persist the paused state across restarts.

#### Scenario: Restart re-enables sync

- **WHEN** the app was closed while paused with pending rows
- **THEN** the next start begins with sync enabled and the normal scheduled cadence applies

### Requirement: Manual sends are an explicit override

The system SHALL treat Debug-panel manual actions (per-table send, send-all, manual screenshot upload, connection test) as explicit user intent that bypasses the pause gate, and the UI SHALL NOT present them as blocked.

#### Scenario: Manual send while paused

- **WHEN** pause is engaged and the user clicks "Send all" with connectivity available
- **THEN** the system uploads the requested tables immediately and reports counts as usual

### Requirement: Pause control and status in both frontends

The system SHALL expose a pause/resume toggle in the Flet window and in the tray menu backed by the same shared gate instance, and both frontends SHALL display an explicit paused status (including pending count) that takes precedence over the normal pending/synced/failed text.

#### Scenario: Flet pill toggles and reports paused

- **WHEN** the user clicks the sync pill while enabled with 40 rows pending
- **THEN** the pill switches to "Sync paused", the status line shows paused with the pending count, and no scheduled POST is issued until resumed

#### Scenario: Tray menu toggles the same gate

- **WHEN** the user selects Pause in the tray menu
- **THEN** scheduled uploads stop, the tray title shows the paused marker, and selecting Resume re-enables with one immediate drain
