"""Load/save TOML config with sane defaults."""
from __future__ import annotations

import os
from pathlib import Path

# NOTE: api_base/api_token/user_id moved to the DB settings table
# (see store.SETTINGS_KEYS); leftover keys in old config.toml files are
# loaded but never read.
DEFAULTS = {
    "screenshot_interval_sec": 900,
    "poll_interval_sec": 360,
    "idle_after_sec": 180,
}

# Previous defaults (pre reduce-capture-rates): migrated to new DEFAULTS on
# load when matched exactly; any other value is user-customized and kept.
_OLD_DEFAULTS = {
    "screenshot_interval_sec": 300,
    "poll_interval_sec": 5,
}

DATA_DIR_ENV = "MOON_TRACKER_DATA_DIR"


def _migrate_dir(old: Path, new: Path) -> Path:
    """One-way move from legacy `worktracker` dirs (keeps sessions + settings)."""
    try:
        if not new.exists() and old.exists():
            old.rename(new)
    except Exception:
        pass  # ponytail: stale data never blocks startup; old dir simply stays
    return new


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    p = _migrate_dir(base / "worktracker", base / "moon-tracker") / "config.toml"
    return p

def default_data_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = _migrate_dir(base / "worktracker", base / "moon-tracker")
    d.mkdir(parents=True, exist_ok=True)
    (d / "shots").mkdir(exist_ok=True)
    return d.resolve()


def data_dir(override: str | Path | None = None) -> Path:
    """Resolve the data dir: flag > MOON_TRACKER_DATA_DIR env > default.

    Relative inputs resolve against cwd; result is absolute with `shots/` created.
    Zero-arg call keeps today's behavior (env > default).
    """
    raw = override if override not in (None, "") else os.environ.get(DATA_DIR_ENV, "")
    if raw not in (None, ""):
        d = Path(raw).expanduser()
        if not d.is_absolute():
            d = Path.cwd() / d
        d = d.resolve()
        d.mkdir(parents=True, exist_ok=True)
        (d / "shots").mkdir(exist_ok=True)
        return d
    return default_data_dir()


def is_default_dir(p: str | Path) -> bool:
    try:
        return Path(p).expanduser().resolve() == default_data_dir()
    except Exception:
        return False


def short_label(p: str | Path) -> str:
    """Compact label for window titles: last two path components."""
    try:
        parts = Path(p).expanduser().resolve().parts
        if len(parts) >= 2:
            return str(Path(*parts[-2:]))
        return Path(p).name or str(p)
    except Exception:
        return str(p)

def load() -> dict:
    cfg = dict(DEFAULTS)
    p = config_path()
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            for k, v in DEFAULTS.items():
                f.write(f'{k} = {v!r}\n'.replace("'", '"') if isinstance(v, str) else f"{k} = {v}\n")
        return cfg
    try:
        import tomllib
        with open(p, "rb") as f:
            cfg.update(tomllib.load(f))
    except Exception:
        pass  # ponytail: corrupt config -> defaults, don't crash tracker
    migrated = False
    for k, old in _OLD_DEFAULTS.items():
        if cfg.get(k) == old:
            cfg[k] = DEFAULTS[k]
            migrated = True
    if migrated:
        try:
            with open(p, "w") as f:
                for k, v in cfg.items():
                    f.write(f'{k} = {v!r}\n'.replace("'", '"') if isinstance(v, str) else f"{k} = {v}\n")
        except Exception:
            pass  # ponytail: rewrite failure never blocks startup; retried next start
    return cfg
