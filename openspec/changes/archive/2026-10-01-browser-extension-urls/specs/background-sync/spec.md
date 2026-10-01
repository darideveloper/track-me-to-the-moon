## ADDED Requirements

### Requirement: Activities payload carries url

The system SHALL include additive `url` (domain, `"(private)"`, or `""`, ≤200 chars) in every `POST /v1/activities` item, keeping sessions → activities → screenshots order, ≤100 rows per POST, and existing ack semantics unchanged.

#### Scenario: Activity with domain syncs

- **WHEN** a pending activity has `url = "github.com"`
- **THEN** the synced item is `{"client_id": "activity:<id>", "session_id": <sid>, "ts": ..., "app": ..., "title": ..., "idle": ..., "url": "github.com", "user_id": ...}` and a full/partial ack marks it uploaded as before

#### Scenario: Old rows without url still sync

- **WHEN** a pending activity has `url = ""` (pre-extension row or non-browser app)
- **THEN** the item is sent with `"url": ""` and accepted normally
