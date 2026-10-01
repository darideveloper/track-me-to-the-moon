## Requirements

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

The system SHALL provide a single eclipse toggle (pill track with sliding moon knob) that creates and closes rows in the `sessions` table via the existing store functions, captioned "Tap to Launch" while stopped and "Tap to Land" while recording (with Start/Stop retained as tooltips). Launch additionally requires valid DB-backed settings (`api_base` an `http(s)` URL, `api_token` and `user_id` non-empty); tapping Launch with invalid settings refuses the session and directs the user to the gear-icon settings view.

#### Scenario: Launch creates a session

- **WHEN** settings are valid and the user taps Launch while stopped
- **THEN** a new `sessions` row is created with `started_at` set and `ended_at` NULL, and the status indicator shows Recording

#### Scenario: Land closes the session

- **WHEN** the user taps Land while recording
- **THEN** the current session row gets `ended_at` set and the status indicator shows Stopped

#### Scenario: Toggle dispatches on state, not disabled buttons

- **WHEN** the tracker is already recording
- **THEN** tapping the toggle lands (stops); and WHEN stopped, tapping launches (starts); no disabled-button states are shown

#### Scenario: Launch refused with invalid settings

- **WHEN** the user taps Launch while any of `api_base`, `api_token`, or `user_id` fails validation
- **THEN** no session row is created, recording does not start, and the UI directs the user to settings

### Requirement: Recent sessions history

The system SHALL show the 10 most recent sessions ordered newest-first, each with a moon-phase leading dot (full when uploaded/synced, crescent when pending), start, end (or "now" if running), and human duration (e.g. `1h 30m`, `45m`), refreshing after Launch/Land and at least every 5 seconds; with no sessions it SHALL show an empty state inviting the user to launch.

#### Scenario: History lists recent sessions

- **WHEN** three sessions exist and the user opens the window
- **THEN** all three appear newest-first with correct start/end/duration

#### Scenario: History updates after Land

- **WHEN** the user lands the current session
- **THEN** the just-ended session appears at the top of the list within 5 seconds

#### Scenario: Running session shows open end

- **WHEN** a session is currently recording
- **THEN** its history row shows start plus an open marker (e.g. `09:00 → now`) instead of a fixed end time

#### Scenario: Rows show sync state

- **WHEN** uploads are pending
- **THEN** unsynced rows show the crescent dot; and WHEN fully synced, rows show the full-moon dot

#### Scenario: Empty history invites launch

- **WHEN** no sessions exist
- **THEN** the list shows "No sessions yet — tap the moon to launch 🚀" instead of a blank area

### Requirement: Small resizable window

The system SHALL open a desktop window titled "Track Me to the Moon" defaulting to approximately 340x560 pixels that is freely resizable, shows the branded window icon when available, with the history area scrolling when content overflows.

#### Scenario: Default size and resize

- **WHEN** the app launches
- **THEN** the window is approximately 340x560 with the branded title; and WHEN the user drags the window edge, the layout reflows and the history list scrolls instead of clipping

### Requirement: Unchanged background tracking

The system SHALL continue polling the active app every `poll_interval_sec`, flagging idle via `idle_after_sec`, taking screenshots every `screenshot_interval_sec` (with jitter), and queueing uploads offline — identical to current tray behavior.

#### Scenario: Activities still recorded

- **WHEN** a session is recording for 10 seconds with default 5s poll
- **THEN** at least one `activities` row exists for that session

### Requirement: Version footer in tracker window

The system SHALL display the runtime version string as a small footer/status line in the Flet tracker window.

#### Scenario: Footer shows current version

- **WHEN** the user opens the tracker window inside the repo
- **THEN** a footer line shows the version string (e.g. `main@a1b2c3d 2026-09-29`) without altering timer, history, or settings behavior

#### Scenario: Footer degrades gracefully

- **WHEN** the version string is `unknown`
- **THEN** the footer shows `unknown` and all other UI functions work normally

### Requirement: URL recording toggle in settings

The system SHALL show a small URL-recording toggle button in the settings view (default ON) that persists immediately and takes effect on the next collector poll without restart, without changing timer, toggle-launch, or history behavior.

#### Scenario: Toggle round-trips

- **WHEN** the user opens settings, flips URL recording OFF, closes, and reopens settings
- **THEN** the toggle still shows OFF and subsequent browser activity rows store `url = ""`

#### Scenario: Invalid settings still gate Launch independently

- **WHEN** URL recording is ON but `api_base`/`api_token`/`user_id` are invalid
- **THEN** Launch is still refused and directed to settings per existing rules; the URL toggle state does not bypass validation
