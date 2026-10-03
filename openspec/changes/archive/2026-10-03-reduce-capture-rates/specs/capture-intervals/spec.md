## ADDED Requirements

### Requirement: Activity capture cadence

The system SHALL record 10 activity rows per hour of continuous running (±1 for boundary timing; one `collect.poll()` + `store.add_activity` per `poll_interval_sec`, default 360s).

#### Scenario: Default activity rate

- **WHEN** tracking runs for 60 minutes with default config and no restart
- **THEN** the `activities` table gains 10 rows (±1 for boundary timing) for that session

#### Scenario: Custom poll interval respected

- **WHEN** `config.toml` sets `poll_interval_sec` to a non-default value (e.g. 60)
- **THEN** the worker loop uses that value and migration does not overwrite it

### Requirement: Screenshot capture cadence

The system SHALL capture at most 4 screenshots per hour of continuous active (non-idle) running (one `shots.take()` per `screenshot_interval_sec`, default 900s, plus jitter).

#### Scenario: Default screenshot rate while active

- **WHEN** tracking runs active (no idle) for 60 minutes with defaults
- **THEN** the `screenshots` table gains 3-4 rows and 3-4 JPEG files appear under `shots/YYYY-MM-DD/`

#### Scenario: No screenshots while idle

- **WHEN** the user is idle (no input for longer than `idle_after_sec`) at a screenshot boundary
- **THEN** the system skips capture for that boundary and records no screenshot row

### Requirement: Screenshot jitter

The system SHALL add a uniform random delay of 0-120s to each screenshot interval so captures are not wall-clock predictable.

#### Scenario: Jitter bounds

- **WHEN** successive screenshot due-times are computed
- **THEN** each gap lies in `[screenshot_interval_sec, screenshot_interval_sec + 120]`

### Requirement: First-run defaults for new installs

The system SHALL create `config.toml` with `poll_interval_sec = 360` and `screenshot_interval_sec = 900` when no config file exists.

#### Scenario: Fresh install gets sparse defaults

- **WHEN** `config.load()` runs with no existing `config.toml`
- **THEN** it writes and returns 360/900 (plus unchanged `idle_after_sec = 180`)

### Requirement: Existing-install migration to sparse rates

The system SHALL migrate existing `config.toml` files that still hold the previous defaults (`poll_interval_sec = 5`, `screenshot_interval_sec = 300`) to the new defaults on load and persist the rewritten file.

#### Scenario: Old defaults auto-upgrade

- **WHEN** `config.load()` reads a file with `poll_interval_sec = 5` and `screenshot_interval_sec = 300`
- **THEN** it returns 360/900 and rewrites the file so the next start keeps sparse rates

#### Scenario: Per-key independent migration

- **WHEN** `config.load()` reads a file where only one interval still holds its old default (e.g. `poll_interval_sec = 5` with a customized `screenshot_interval_sec`)
- **THEN** it migrates only the old-default key and leaves the customized key untouched

#### Scenario: Customized values preserved

- **WHEN** `config.load()` reads a file with any non-old-default interval (e.g. `poll_interval_sec = 60`)
- **THEN** it leaves that value untouched and does not rewrite it to 360
