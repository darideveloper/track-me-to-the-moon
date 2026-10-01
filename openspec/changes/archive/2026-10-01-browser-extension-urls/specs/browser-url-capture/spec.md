## ADDED Requirements

### Requirement: Domain-only capture via extension and loopback

The system SHALL capture the active tab domain (hostname only, never path/query) from a browser extension via a localhost listener and attach it to activity rows.

#### Scenario: Tab change enriches next activity row

- **WHEN** the extension POSTs `{"domain": "github.com", "ts": "<now>", "browser": "chrome"}` to `127.0.0.1:42813` and the next 5s collector poll sees a browser foreground app while URL recording is ON
- **THEN** the inserted `activities` row has `url = "github.com"`

#### Scenario: Stale events are not attached

- **WHEN** the last extension event is older than 10 seconds at poll time
- **THEN** the activity row is written with `url = ""`

#### Scenario: Non-browser apps never get a URL

- **WHEN** the foreground app is not a known browser (e.g. `Code`, `Slack`)
- **THEN** the activity row is written with `url = ""` even if a recent domain event exists

#### Scenario: Private tabs record a marker

- **WHEN** the active tab is incognito/private
- **THEN** the extension sends domain `"(private)"` and the activity row stores `url = "(private)"`

#### Scenario: Missing extension degrades silently

- **WHEN** no extension event was ever received (or the loopback failed to bind)
- **THEN** collection, screenshots, and sync continue unchanged with `url = ""` and no error surfacing

### Requirement: URL recording toggle

The system SHALL provide a small on/off toggle button for URL recording in the settings UI, defaulting to ON, persisted and honored without restart.

#### Scenario: Toggle OFF stops enrichment

- **WHEN** the user switches URL recording OFF and a fresh domain event arrives before the next poll
- **THEN** the next activity row is written with `url = ""`

#### Scenario: Toggle persists across restarts

- **WHEN** the user sets URL recording OFF, restarts the app, and a domain event arrives
- **THEN** enrichment stays OFF until toggled back ON

### Requirement: Loopback listener behavior

The system SHALL expose `POST http://127.0.0.1:42813/url` on the loopback interface only, accepting JSON `{domain, ts, browser}` and rejecting malformed input without affecting tracking.

#### Scenario: Malformed POST is ignored safely

- **WHEN** a POST arrives with invalid JSON, missing `domain`, or body over 4KB
- **THEN** the server responds `400` (or `200 {"ignored":true}` when recording is OFF) and the collector state is unchanged

#### Scenario: Listener never binds externally

- **WHEN** the tracker starts with the port already in use or on any host
- **THEN** it binds `127.0.0.1` only (never `0.0.0.0`), logs a warning on conflict, and tracking continues with `url = ""`
