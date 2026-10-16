## MODIFIED Requirements

### Requirement: Screenshot retention and cleanup

The system SHALL keep uploaded screenshot JPEGs for 7 days after ack, then a daily cleanup pass deletes the files and their rows; unsent rows and files are never auto-deleted. The daily cleanup pass SHALL run on its own daily gate independent of upload activity, including while the sync-pause gate is engaged.

#### Scenario: Post-ack retention

- **WHEN** a screenshot was acked 3 days ago
- **THEN** its file and row remain locally

#### Scenario: Expired cleanup

- **WHEN** a screenshot was acked 8 days ago
- **THEN** the daily cleanup deletes its JPEG file and removes its row

#### Scenario: Cleanup runs while paused

- **WHEN** pause has been engaged for 3 days and an acked screenshot passes 7 days old
- **THEN** the next daily cleanup pass deletes its JPEG file and removes its row without issuing any upload
