## ADDED Requirements

### Requirement: Gear-icon entry to settings

The system SHALL show a gear icon at the top-left of the home view that navigates to a settings view, which provides a Back action returning to home. Field values are repopulated from the database on every navigation to settings.

#### Scenario: Open and return

- **WHEN** the user taps the gear icon and then Back
- **THEN** the settings view appears with current stored values, and Back restores the home view unchanged

### Requirement: Editable identity fields with strict validation

The settings view SHALL provide editable `api_base` and `user_id` fields plus a single Save that commits atomically, enforcing on Save that `api_base` is an `http(s)` URL and `user_id` is non-empty after trimming; invalid input blocks the entire save (no field is written) and shows which field failed.

#### Scenario: Invalid base URL blocked

- **WHEN** the user saves `api_base = "not-a-url"` with a valid `user_id`
- **THEN** no field is written (atomic block) and the view reports the `api_base` error

#### Scenario: Empty user id blocked

- **WHEN** the user saves `user_id = "   "` (whitespace only)
- **THEN** no field is written (atomic block) and the view reports the `user_id` error

#### Scenario: Valid save persists trimmed values

- **WHEN** the user saves `api_base = "  https://api.example.com  "` and `user_id = " emp-042 "`
- **THEN** the stored values are `"https://api.example.com"` and `"emp-042"` and the view confirms success

### Requirement: Masked token with Change flow

The `api_token` field SHALL render as a non-revealing password input showing only bullets after a value is saved, with editing disabled until the user taps an explicit Change action that clears it to an empty input; saving from the Change state overwrites the stored token, and empty-token saves are rejected.

#### Scenario: Saved token is masked and locked

- **WHEN** a token is stored and the user opens settings
- **THEN** the token field shows bullets only, reveal is unavailable, and Save for the token is disabled until Change is tapped

#### Scenario: Change overwrites token

- **WHEN** the user taps Change, enters `"new-secret"`, and saves
- **THEN** the stored `api_token` becomes `"new-secret"` and the field returns to masked/locked

#### Scenario: Empty token rejected

- **WHEN** the user attempts to save an empty token
- **THEN** the stored token is unchanged and the view reports the error

### Requirement: Incomplete-settings hint on home

The home view SHALL show a persistent "settings incomplete" hint whenever any of the 3 keys fails validation, pointing at the gear icon, until settings become valid.

#### Scenario: Hint clears after valid save

- **WHEN** settings are incomplete and the user saves all 3 keys valid
- **THEN** the home hint disappears
