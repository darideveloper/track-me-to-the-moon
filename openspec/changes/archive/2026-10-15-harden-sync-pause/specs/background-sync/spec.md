## MODIFIED Requirements

### Requirement: Close flush with user message

The system SHALL, on app close/quit, stop the collector first then run a blocking flush of up to 30 seconds showing a user-visible "Syncing…" message with remaining count, then exit regardless of remainder. When the sync-pause gate is engaged at close time, the system SHALL skip the flush entirely, keep all rows pending, and show a user-visible "paused — N items kept for next start" message instead.

#### Scenario: Close with small backlog

- **WHEN** the user closes the app with 40 pending activities and connectivity available
- **THEN** the system displays a syncing message, uploads them within 30s, marks acked rows sent, and exits

#### Scenario: Close with huge backlog

- **WHEN** the user closes the app with pending data exceeding the 30s budget
- **THEN** the system uploads what fits in 30s, shows remaining count, exits, and leaves the rest pending for next start

#### Scenario: Close while paused keeps data local

- **WHEN** the user closes the app while paused with 40 pending activities and connectivity available
- **THEN** the system issues no POSTs, shows a paused message with the kept count, exits promptly, and leaves all rows pending for next start
