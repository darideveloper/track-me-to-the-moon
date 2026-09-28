## ADDED Requirements

### Requirement: Outbox tracking per row

The system SHALL persist `uploaded`, `upload_attempts`, `last_error`, `uploaded_at` on sessions, activities, and screenshots, query pending rows as `WHERE uploaded=0 ORDER BY id ASC`, and fix the current newest-first/broken-`synced_activities` behavior.

#### Scenario: Oldest pending selected

- **WHEN** 500 activities are pending and a chunk is requested
- **THEN** the system returns the 100 lowest-id unuploaded rows

#### Scenario: Attempts and errors recorded

- **WHEN** a chunk POST fails retryably
- **THEN** the system increments `upload_attempts` and stores `last_error` without marking rows uploaded

### Requirement: Ack-only marking with idempotency

The system SHALL send `client_id` (`{table}:{id}`) with every row, and mark rows `uploaded=1` with `uploaded_at` timestamp only for ids listed in a valid ack body (`200` + `ok:true` + `accepted` list); partial acks mark only accepted ids and anything else marks nothing. Fallback: `200` + `ok:true` with no `accepted` list (all-or-nothing backend) marks the whole chunk uploaded.

#### Scenario: Full ack marks chunk

- **WHEN** 100 activities are POSTed and the backend returns `200 { ok:true, accepted:[all 100 ids] }`
- **THEN** all 100 rows become `uploaded=1` in one transaction with a ledger entry

#### Scenario: Partial ack marks subset

- **WHEN** the backend accepts 90 of 100 ids
- **THEN** only those 90 rows are marked uploaded and the remaining 10 stay pending with no error increment beyond the run

#### Scenario: Invalid response marks nothing

- **WHEN** the backend returns non-200, `ok:false`, or `ok:true` with an `accepted` list that omits some chunk ids
- **THEN** unlisted rows stay pending (omitted ids are not marked) and the failure is recorded for retry

#### Scenario: All-or-nothing fallback

- **WHEN** the backend returns `200 { ok:true }` with no `accepted` list
- **THEN** the whole chunk is marked uploaded in one transaction with a ledger entry

### Requirement: Retry forever with failure classification

The system SHALL retry unsent rows forever across restarts, treat 5xx/timeout/429 as retryable, treat other 4xx as auth/config pauses (no hot retry, surface settings hint), and write one `sync_runs` ledger row per run with counts and error.

#### Scenario: Transient failure retries next tick

- **WHEN** a run fails with timeout
- **THEN** rows stay pending, the ledger records the error, and the next 10-minute tick retries them

#### Scenario: Auth failure pauses

- **WHEN** the backend returns 401
- **THEN** the system records the error, surfaces a settings hint, does not tight-loop retry, and retries on the next scheduled tick

### Requirement: Throttled failure notification

The system SHALL raise an OS-level notification on sync failure at most once per calendar day per failure kind, mirrored in-app when the window is open.

#### Scenario: Repeated failures notify once

- **WHEN** three consecutive 10-minute runs fail with network errors on the same day
- **THEN** the user receives exactly one system notification that day plus an in-app hint

#### Scenario: Next day re-notifies

- **WHEN** failures continue into the next calendar day
- **THEN** the system raises one fresh notification for the new day

### Requirement: Screenshot retention and cleanup

The system SHALL keep uploaded screenshot JPEGs for 7 days after ack, then a daily cleanup pass deletes the files and their rows; unsent rows and files are never auto-deleted.

#### Scenario: Post-ack retention

- **WHEN** a screenshot was acked 3 days ago
- **THEN** its file and row remain locally

#### Scenario: Expired cleanup

- **WHEN** a screenshot was acked 8 days ago
- **THEN** the daily cleanup deletes its JPEG file and removes its row

### Requirement: Thread-safe store access

The system SHALL serialize all SQLite access through a shared lock so collector inserts and sync reads/marks cannot interleave corruptly.

#### Scenario: Concurrent collect and sync

- **WHEN** the collector inserts an activity while a sync chunk is being marked uploaded
- **THEN** both operations complete without `database is locked` errors or lost writes
