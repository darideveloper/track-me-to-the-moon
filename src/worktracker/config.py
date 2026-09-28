"""Load/save TOML config with sane defaults."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULTS = {
    "api_base": "",
    "api_token": "",
    "user_id": "",
    "screenshot_interval_sec": 300,
    "poll_interval_sec": 5,
    "idle_after_sec": 180,
}

def config_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "worktracker" / "config.toml"

def data_dir() -> Path:
    d = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "worktracker"
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
    return cfg
