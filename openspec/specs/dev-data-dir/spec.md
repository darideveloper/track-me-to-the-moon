## Requirements

### Requirement: Data-dir override selection

The system SHALL resolve the data directory (containing `tracker.db` and `shots/`) with precedence `--data-dir` flag > `MOON_TRACKER_DATA_DIR` env > default (`$XDG_DATA_HOME or ~/.local/share` + `/moon-tracker`), normalizing relative inputs against cwd to absolute paths and creating the dir plus `shots/` on start.

#### Scenario: Flag wins over env and default

- **WHEN** the user runs with `--data-dir dev-data` while `MOON_TRACKER_DATA_DIR=/other` is set
- **THEN** the process uses `<cwd>/dev-data` (resolved absolute) for `tracker.db` and `shots/`

#### Scenario: Env fallback works without flag

- **WHEN** no flag is passed and `MOON_TRACKER_DATA_DIR=/tmp/mt-dev` is set
- **THEN** the process uses `/tmp/mt-dev` for `tracker.db` and `shots/`

#### Scenario: Default unchanged without override

- **WHEN** neither flag nor env is set
- **THEN** the process uses the existing default path with identical behavior to today (no badge, same DB)

#### Scenario: Startup logs the resolved dir

- **WHEN** the app starts (Flet, tray, `--once`, `--shot`)
- **THEN** it prints/logs `data dir: <absolute path>` so the operator can verify the environment before Launch

### Requirement: Per-dir isolation of DB, shots, and settings

The system SHALL keep `tracker.db` (sessions, activities, screenshots, settings) and `shots/YYYY-MM-DD/HH-MM-SS.jpg` fully inside the resolved data dir, so two processes on different dirs never share rows, credentials, or files; timing intervals remain shared via the global `config.toml`.

#### Scenario: Dev DB starts empty and remembers settings

- **WHEN** the user launches with a fresh `--data-dir dev-data` and opens settings
- **THEN** `api_base`/`api_token`/`user_id` read empty (dev triple entered via Save), and after Save + restart with the same dir the values persist

#### Scenario: Concurrent prod and dev record independently

- **WHEN** prod (default) and dev (`dev-data`) record simultaneously
- **THEN** each writes activities/screenshots only to its own `tracker.db`/`shots/` and uploads with its own `user_id`; prod sessions are never force-ended by a dev Launch

#### Scenario: Screenshot helpers honor the injected dir

- **WHEN** the background worker or manual screenshot fires in a dev process
- **THEN** the JPEG is written under the dev `shots/` dir and queued against the dev DB session (never the default dir)

### Requirement: Dev-mode badge (Flet title + footer, tray title)

The system SHALL display a dev indicator whenever the resolved data dir differs from the default (after symlink normalization): Flet window title gains suffix `[🧪 <label>]` where `<label>` is the last two path components, the version footer gains `· <absolute path>`, and the tray title gains the same suffix; default runs show no badge.

#### Scenario: Dev Flet window is labeled

- **WHEN** Flet starts with `--data-dir dev-data`
- **THEN** the window title contains `[🧪` plus a short path label, and the footer line contains the absolute dev path

#### Scenario: Prod window unchanged

- **WHEN** Flet starts with no override
- **THEN** title is exactly `Track Me to the Moon` and footer shows only the version string

#### Scenario: Tray title labeled in dev

- **WHEN** tray mode runs with a non-default dir
- **THEN** the tray tooltip/title includes the dev suffix with pending/synced state preserved

### Requirement: Dev skips OS launcher rewrite

The system SHALL skip rewriting `~/.local/share/applications/moon-tracker.desktop` and patching the Flet client icon when running on a non-default data dir.

#### Scenario: Dev launch leaves prod launcher intact

- **WHEN** Flet starts with `--data-dir dev-data`
- **THEN** the `.desktop` `Exec=` line and installed icon are untouched (mtime/content unchanged)

### Requirement: Dev-data ignored by git

The system SHALL ignore the conventional `dev-data/` directory so a repo-local dev environment never pollutes `git status` or gets committed.

#### Scenario: Fresh dev-data is invisible to git

- **WHEN** `dev-data/tracker.db` exists and the user runs `git status --short`
- **THEN** no `dev-data` entries appear

### Requirement: Debug bundle identifies data dir

The system SHALL include the resolved absolute data-dir path in the debug `Copy bundle` output so dev vs prod bug reports are distinguishable.

#### Scenario: Bundle shows which environment it came from

- **WHEN** the user copies the debug bundle from a dev process
- **THEN** the bundle text contains the absolute dev data-dir path
