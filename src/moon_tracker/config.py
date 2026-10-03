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

def data_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = _migrate_dir(base / "worktracker", base / "moon-tracker")
    d.mkdir(parents=True, exist_ok=True)
    (d / "shots").mkdir(exist_ok=True)
    return d

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
