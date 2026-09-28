## Requirements

### Requirement: Ten-minute chunked sync cadence

The system SHALL run background sync every 600 seconds with ±30s jitter, draining in order sessions → activities → screenshots, with at most 100 JSON rows per POST and 1 screenshot per POST, bounding each run to ~120s or 10 chunks with leftovers deferred to the next tick.

#### Scenario: Scheduled tick drains oldest first

- **WHEN** the 10-minute timer fires with 250 pending activities and 3 pending screenshots
- **THEN** the system POSTs activities as chunks of 100, 100, 50 oldest-first, then POSTs screenshots one-by-one, and stops at the run cap with remainder left pending

#### Scenario: Open session syncs as snapshot

- **WHEN** a session is still running (`ended_at` is null) at tick time
- **THEN** the system uploads it as a snapshot with `ended_at:null`, leaves it pending (`uploaded=0`), and re-uploads the final times after Stop/close

#### Scenario: Run budget respected

- **WHEN** a run exceeds ~120s or 10 chunks with items still pending
- **THEN** the system stops the run, leaves remaining rows `uploaded=0`, and schedules them for the next tick

### Requirement: Close flush with user message

The system SHALL, on app close/quit, stop the collector first then run a blocking flush of up to 30 seconds showing a user-visible "Syncing…" message with remaining count, then exit regardless of remainder.

#### Scenario: Close with small backlog

- **WHEN** the user closes the app with 40 pending activities and connectivity available
- **THEN** the system displays a syncing message, uploads them within 30s, marks acked rows sent, and exits

#### Scenario: Close with huge backlog

- **WHEN** the user closes the app with pending data exceeding the 30s budget
- **THEN** the system uploads what fits in 30s, shows remaining count, exits, and leaves the rest pending for next start

### Requirement: Offline queueing

The system SHALL keep queueing locally without error when `api_base` is empty or network is unavailable.

#### Scenario: No backend configured

- **WHEN** `api_base` is empty
- **THEN** the sync tick does nothing, rows stay pending, and no notification is raised
