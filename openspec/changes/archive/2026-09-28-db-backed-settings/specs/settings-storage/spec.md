## ADDED Requirements

### Requirement: Settings singleton table

The system SHALL persist exactly the keys `api_base`, `api_token`, and `user_id` in a `settings(key TEXT PRIMARY KEY, value TEXT)` table inside `tracker.db`, auto-created on connect alongside existing tables.

#### Scenario: Table auto-creates on existing database

- **WHEN** `store.connect()` opens a database created by an older version
- **THEN** the `settings` table exists afterwards and prior sessions data is untouched

#### Scenario: Unknown keys are rejected

- **WHEN** a caller writes a key other than `api_base`, `api_token`, or `user_id`
- **THEN** the write is rejected with an error and no row is created

#### Scenario: Existing TOML values are never imported

- **WHEN** a `config.toml` already contains values for these keys
- **THEN** connecting and reading settings ignores the TOML values entirely (clean break; settings start empty until entered in the UI)

### Requirement: Settings accessors

The system SHALL provide `get_setting(con, key)`, `set_setting(con, key, value)`, and `get_settings_dict(con)` helpers where missing keys read as `""`, written values are stored trimmed, and every write commits immediately.

#### Scenario: Round-trip with trimming

- **WHEN** `set_setting(con, "user_id", "  emp-042  ")` is called
- **THEN** `get_setting(con, "user_id")` returns `"emp-042"`

#### Scenario: Missing key reads as empty

- **WHEN** no value was ever stored for `api_token`
- **THEN** `get_setting(con, "api_token")` returns `""` and `get_settings_dict(con)` includes `"api_token": ""`

### Requirement: Readers observe latest saved values

Background upload and collector cycles SHALL read settings from the database on each cycle rather than relying on a cached dict, so a UI save is visible to the next cycle without restart.

#### Scenario: Save propagates without restart

- **WHEN** the user saves a new `api_base` while the uploader thread is running
- **THEN** the next drain cycle uses the new `api_base`
