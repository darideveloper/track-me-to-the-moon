## Requirements

### Requirement: Debug entry in header

The system SHALL provide a brand-styled debug button in the Flet header (next to the settings gear) that toggles a full third debug view (same show/hide pattern as settings, not an overlay dialog) and preserves timer, toggle, history, and settings behavior.

#### Scenario: Open debug view
- **WHEN** the user taps the debug button from home
- **THEN** the home view hides, the debug view shows, and tapping back returns to home with timer uninterrupted

#### Scenario: Brand match
- **WHEN** the header renders in light or dark mode
- **THEN** the debug icon uses the same `MOON_WHITE` icon color and night-sky header style as the gear/theme buttons

### Requirement: Manual screenshot now

The system SHALL provide a Take-screenshot action that captures via the existing screenshot pipeline, attaches to the active session when recording otherwise to the most recent session, queues the row in the outbox, and triggers an immediate screenshots-stage drain, working even when tracking is Stopped; when no session exists yet it SHALL refuse with a hint and queue nothing.

#### Scenario: Screenshot queued and sent
- **WHEN** the user taps Take screenshot with connectivity and 2 pending screenshots
- **THEN** a new screenshot file + `screenshots` row appear and a `POST /v1/screenshots` is attempted within seconds with the result logged

#### Scenario: Works while stopped
- **WHEN** tracking is Stopped and at least one prior session exists and the user taps Take screenshot
- **THEN** the capture attaches to the most recent session id, queues, and uploads without starting a new session

#### Scenario: Refuses with no session yet
- **WHEN** tracking is Stopped, no session row exists yet, and the user taps Take screenshot
- **THEN** no file or row is created and the UI shows a hint to Launch first

### Requirement: Per-type manual send

The system SHALL provide per-type Send actions (Sessions, Activities, Screenshots, Send all) that run the existing chunked drain with ack-only marking for the selected tables and `reason="manual"`, working even when Stopped; with no `api_base` configured the action SHALL log a skipped entry and leave rows pending.

#### Scenario: Send activities only
- **WHEN** the user taps Send Activities with 150 pending activities and 3 pending sessions
- **THEN** activities drain in 100 + 50 chunks with ack marking while sessions remain pending, and the ledger records a `manual` run

#### Scenario: Send all drains in order
- **WHEN** the user taps Send all
- **THEN** the system drains sessions → activities → screenshots honoring the existing per-run chunk caps with remainder left pending

#### Scenario: Skipped without backend
- **WHEN** the user taps any Send with empty `api_base`
- **THEN** the log shows a skipped entry, rows stay pending, and no error notification is raised

### Requirement: Connection ping

The system SHALL provide a Test connection action that first attempts `GET {api_base}/health` and on non-2xx/network fallback sends an empty `POST /v1/sessions` probe, logging the HTTP status or error independently of outbox contents without marking any rows uploaded.

#### Scenario: Reachable backend
- **WHEN** the user taps Test connection with valid settings and network
- **THEN** the log shows the probe endpoint plus status (e.g. `GET /health ← 200`) within the API timeout

#### Scenario: Unreachable backend
- **WHEN** the backend is down or settings are invalid
- **THEN** the log shows the error (timeout / http 401 / no api_base) and no outbox rows change state

#### Scenario: Health endpoint missing
- **WHEN** `GET /health` returns 404 and outbox is empty
- **THEN** the system falls back to the empty sessions probe and logs that result instead of failing

### Requirement: Live API call log

The system SHALL maintain a session-only in-memory ring of the last 200 API calls, rendered newest-first as compact rows with tap-to-expand truncated payload/response, updated at least every 2 seconds while the debug view is visible.

#### Scenario: Scheduled tick appears
- **WHEN** a background 10-minute tick POSTs 12 activities with full ack
- **THEN** a row `POST /v1/activities → 12 items ← 200 accepted:12` appears with expandable previews

#### Scenario: Failure surfaces error
- **WHEN** a POST returns 401
- **THEN** the row shows `← 401 http 401 (auth_error)` and the existing `sync_text` failed hint remains consistent

#### Scenario: Ring bound respected
- **WHEN** 250 calls occur in one session
- **THEN** only the newest 200 are retained and the view stays scrollable

### Requirement: Token redaction and truncation

The system SHALL never include the raw API token or Authorization header in any log entry, preview, or copied bundle, and SHALL truncate request previews to 2KB and response previews to 1KB with an explicit truncated marker.

#### Scenario: Token absent from log
- **WHEN** any authenticated call is logged or the bundle is copied
- **THEN** no entry contains the token value; auth is shown only as `present/missing`

#### Scenario: Large payload truncated
- **WHEN** a 100-item activities chunk is logged
- **THEN** the preview ends with a truncation marker and byte/item counts instead of the full JSON

### Requirement: Copy bundle and clear

The system SHALL provide Copy debug bundle (version + pending counts + last sync summary + last 20 log lines, token stripped, via clipboard) and Clear log (empties the ring only, never the outbox).

#### Scenario: Bundle copied
- **WHEN** the user taps Copy after 3 logged calls
- **THEN** the clipboard holds a paste-ready report with version, pending counts, last error, and the 3 calls

#### Scenario: Clear is safe
- **WHEN** the user taps Clear with 50 pending activities
- **THEN** the log empties to zero rows while all 50 activities remain pending in the outbox
