## ADDED Requirements

### Requirement: URL recording toggle in settings

The system SHALL show a small URL-recording toggle button in the settings view (default ON) that persists immediately and takes effect on the next collector poll without restart, without changing timer, toggle-launch, or history behavior.

#### Scenario: Toggle round-trips

- **WHEN** the user opens settings, flips URL recording OFF, closes, and reopens settings
- **THEN** the toggle still shows OFF and subsequent browser activity rows store `url = ""`

#### Scenario: Invalid settings still gate Launch independently

- **WHEN** URL recording is ON but `api_base`/`api_token`/`user_id` are invalid
- **THEN** Launch is still refused and directed to settings per existing rules; the URL toggle state does not bypass validation
