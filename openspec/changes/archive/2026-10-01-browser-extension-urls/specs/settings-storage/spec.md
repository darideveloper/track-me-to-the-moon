## MODIFIED Requirements

### Requirement: Settings singleton table

The system SHALL persist exactly the keys `api_base`, `api_token`, `user_id`, and `record_urls` in a `settings(key TEXT PRIMARY KEY, value TEXT)` table inside `tracker.db`, auto-created on connect alongside existing tables. `record_urls` holds `"1"` (on) or `"0"` (off) and defaults to `"1"` when never written.

#### Scenario: Table auto-creates on existing database

- **WHEN** `store.connect()` opens a database created by an older version
- **THEN** the `settings` table exists afterwards and prior sessions data is untouched

#### Scenario: Unknown keys are rejected

- **WHEN** a caller writes a key other than `api_base`, `api_token`, `user_id`, or `record_urls`
- **THEN** the write is rejected with an error and no row is created

#### Scenario: Existing TOML values are never imported

- **WHEN** a `config.toml` already contains values for these keys
- **THEN** connecting and reading settings ignores the TOML values entirely (clean break; settings start empty until entered in the UI, except `record_urls` which reads as `"1"` until explicitly set)

### Requirement: Settings accessors

The system SHALL provide `get_setting(con, key)`, `set_setting(con, key, value)`, and `get_settings_dict(con)` helpers where missing keys read as `""` (except `record_urls`, which reads as `"1"`), written values are stored trimmed, and every write commits immediately. `set_setting(con, "record_urls", value)` SHALL reject values other than `"1"`/`"0"` (and boolean-equivalent trimmed inputs mapped by the UI layer) with an error.

#### Scenario: Round-trip with trimming

- **WHEN** `set_setting(con, "user_id", "  emp-042  ")` is called
- **THEN** `get_setting(con, "user_id")` returns `"emp-042"`

#### Scenario: Missing key reads as empty

- **WHEN** no value was ever stored for `api_token`
- **THEN** `get_setting(con, "api_token")` returns `""` and `get_settings_dict(con)` includes `"api_token": ""`

#### Scenario: record_urls defaults on and round-trips

- **WHEN** no value was ever stored for `record_urls`
- **THEN** `get_setting(con, "record_urls")` returns `"1"`; and WHEN `set_setting(con, "record_urls", "0")` is called THEN subsequent reads return `"0"`
