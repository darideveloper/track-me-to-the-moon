## ADDED Requirements

### Requirement: Live timer display

The system SHALL display the current session elapsed time as `HH:MM:SS`, updating every second while recording, and `00:00:00` when stopped.

#### Scenario: Timer ticks while recording

- **WHEN** the user clicks Start and 3 seconds elapse
- **THEN** the timer shows `00:00:03` (within 1s tolerance)

#### Scenario: Timer freezes on Stop

- **WHEN** the user clicks Stop
- **THEN** the timer freezes at its final value and the status shows Stopped

#### Scenario: Timer resets on next Start

- **WHEN** the user clicks Start after a previous session
- **THEN** the timer resets to `00:00:00` and starts ticking

### Requirement: Start and Stop controls

The system SHALL provide Start and Stop buttons that create and close rows in the `sessions` table via the existing store functions, with buttons disabled in invalid states (Start disabled while recording, Stop disabled while stopped).

#### Scenario: Start creates a session

- **WHEN** the user clicks Start while stopped
- **THEN** a new `sessions` row is created with `started_at` set and `ended_at` NULL, and the status indicator shows Recording

#### Scenario: Stop closes the session

- **WHEN** the user clicks Stop while recording
- **THEN** the current session row gets `ended_at` set and the status indicator shows Stopped

#### Scenario: Invalid button states are blocked

- **WHEN** the tracker is already recording
- **THEN** the Start button is disabled; and WHEN stopped, the Stop button is disabled

### Requirement: Recent sessions history

The system SHALL show the 10 most recent sessions ordered newest-first, each with start, end (or "now" if running), and human duration (e.g. `1h 30m`, `45m`), refreshing after Start/Stop and at least every 5 seconds.

#### Scenario: History lists recent sessions

- **WHEN** three sessions exist and the user opens the window
- **THEN** all three appear newest-first with correct start/end/duration

#### Scenario: History updates after Stop

- **WHEN** the user stops the current session
- **THEN** the just-ended session appears at the top of the list within 5 seconds

#### Scenario: Running session shows open end

- **WHEN** a session is currently recording
- **THEN** its history row shows start plus an open marker (e.g. `09:00 → now`) instead of a fixed end time

### Requirement: Small resizable window

The system SHALL open a desktop window defaulting to approximately 320x450 pixels that is freely resizable, with the history area scrolling when content overflows.

#### Scenario: Default size and resize

- **WHEN** the app launches
- **THEN** the window is approximately 320x450; and WHEN the user drags the window edge, the layout reflows and the history list scrolls instead of clipping

### Requirement: Unchanged background tracking

The system SHALL continue polling the active app every `poll_interval_sec`, flagging idle via `idle_after_sec`, taking screenshots every `screenshot_interval_sec` (with jitter), and queueing uploads offline — identical to current tray behavior.

#### Scenario: Activities still recorded

- **WHEN** a session is recording for 10 seconds with default 5s poll
- **THEN** at least one `activities` row exists for that session
