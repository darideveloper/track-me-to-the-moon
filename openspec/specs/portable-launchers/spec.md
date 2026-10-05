## Requirements

### Requirement: Windows double-click launcher

The system SHALL provide a `run.bat` at repo root that bootstraps and starts the tracker with no manual venv steps. All CLI arguments SHALL be forwarded to the app, so `run.bat --data-dir dev-data` selects an isolated data dir.

#### Scenario: First run bootstraps everything

- **WHEN** the user double-clicks `run.bat` on a PC with git and Python 3.10+ but no `uv`
- **THEN** the script installs `uv` to the user profile, runs `uv sync --frozen`, prints a first-run download notice, and opens the Flet window

#### Scenario: Missing git stops with guidance

- **WHEN** `git` is not on PATH
- **THEN** the script prints the git-scm.com download link and exits non-zero without creating a partial venv

#### Scenario: Old Python is provisioned, not failed

- **WHEN** no Python >= 3.10 is found but `uv` is available
- **THEN** the script runs `uv python install 3.12` and uses it instead of aborting

#### Scenario: Repeat run is fast

- **WHEN** `.venv` already exists and `uv.lock` is unchanged
- **THEN** the script skips re-download and starts the app in seconds

#### Scenario: Branch guard warns off-main

- **WHEN** the checkout branch is not `main`
- **THEN** the script prints a "not on main" warning and continues to launch without switching branches

#### Scenario: Data-dir flag flows to dev environment on Windows

- **WHEN** the user runs `run.bat --data-dir dev-data`
- **THEN** the app starts with `<repo>\dev-data` as its data dir (DB + shots isolated) while bootstrap/sync behavior is unchanged

### Requirement: Linux launcher with session warning

The system SHALL provide an executable `run.sh` at repo root with the same bootstrap flow plus Linux-specific checks. All CLI arguments SHALL be forwarded to the app (`python -m moon_tracker "$@"`), so `./run.sh --data-dir dev-data` selects an isolated data dir.

#### Scenario: Wayland warns but continues

- **WHEN** `$XDG_SESSION_TYPE` is `wayland`
- **THEN** the script prints "window titles best-effort, X11 recommended" and continues to launch

#### Scenario: Missing Xlib hints system package

- **WHEN** `python3-xlib` import fails after sync on Linux
- **THEN** the script prints the distro install hint (`sudo apt install python3-xlib`) while still attempting launch

#### Scenario: Branch guard warns off-main

- **WHEN** the checkout branch is not `main`
- **THEN** the script prints a "not on main" warning and continues to launch without switching branches

#### Scenario: Data-dir flag flows to dev environment

- **WHEN** the user runs `./run.sh --data-dir dev-data`
- **THEN** the app starts with `<repo>/dev-data` as its data dir (DB + shots isolated) while bootstrap/sync behavior is unchanged

### Requirement: Pull-to-update flow

The system SHALL support updating by `git pull --ff-only` followed by launcher re-sync, with user data preserved.

#### Scenario: Clean update succeeds

- **WHEN** the working tree is clean and the user runs `git pull --ff-only` then `run.bat`/`run.sh`
- **THEN** new code runs after an automatic `uv sync`, and `tracker.db` settings and sessions are intact

#### Scenario: Dirty tree aborts safely

- **WHEN** the working tree has local modifications and the user runs `git pull --ff-only` per the README update flow
- **THEN** git refuses the fast-forward and aborts, leaving the working tree and `tracker.db` untouched (no stash, no reset; the user commits or stashes first, then re-pulls)

### Requirement: Reproducible lockfile

The system SHALL commit a `uv.lock` generated from `pyproject.toml` so teammate machines resolve identical dependency versions.

#### Scenario: Frozen sync reproduces dev env

- **WHEN** a teammate runs the launcher with the committed `uv.lock`
- **THEN** `uv sync --frozen` installs the same pinned versions (including `flet==1.0.1`) as the dev machine

#### Scenario: Smoke command validates install

- **WHEN** the user runs the synced env with `python -m moon_tracker --once`
- **THEN** one poll prints and the process exits zero without opening the UI
