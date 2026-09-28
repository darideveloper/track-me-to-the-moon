## MODIFIED Requirements

### Requirement: Start and Stop controls

The system SHALL provide Start and Stop buttons that create and close rows in the `sessions` table via the existing store functions, with buttons disabled in invalid states (Start disabled while recording, Stop disabled while stopped). Start additionally requires valid DB-backed settings (`api_base` an `http(s)` URL, `api_token` and `user_id` non-empty); pressing Start with invalid settings refuses the session and directs the user to the gear-icon settings view.

#### Scenario: Start creates a session

- **WHEN** settings are valid and the user clicks Start while stopped
- **THEN** a new `sessions` row is created with `started_at` set and `ended_at` NULL, and the status indicator shows Recording

#### Scenario: Stop closes the session

- **WHEN** the user clicks Stop while recording
- **THEN** the current session row gets `ended_at` set and the status indicator shows Stopped

#### Scenario: Invalid button states are blocked

- **WHEN** the tracker is already recording
- **THEN** the Start button is disabled; and WHEN stopped, the Stop button is disabled

#### Scenario: Start refused with invalid settings

- **WHEN** the user clicks Start while any of `api_base`, `api_token`, or `user_id` fails validation
- **THEN** no session row is created, recording does not start, and the UI directs the user to settings
