"""Capture intervals (reduce-capture-rates): sparse defaults + old-default migration."""
from pathlib import Path

from moon_tracker import config


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))


def test_fresh_install_writes_sparse_defaults(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    cfg = config.load()
    assert cfg["poll_interval_sec"] == 360
    assert cfg["screenshot_interval_sec"] == 900
    assert cfg["idle_after_sec"] == 180
    text = (tmp_path / "cfg" / "moon-tracker" / "config.toml").read_text()
    assert "poll_interval_sec = 360" in text
    assert "screenshot_interval_sec = 900" in text


def test_old_defaults_migrate_and_persist(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    p = config.config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("screenshot_interval_sec = 300\npoll_interval_sec = 5\nidle_after_sec = 180\n")
    cfg = config.load()
    assert cfg["poll_interval_sec"] == 360
    assert cfg["screenshot_interval_sec"] == 900
    assert cfg["idle_after_sec"] == 180
    # Second load keeps sparse rates (migration persisted, not re-applied).
    cfg2 = config.load()
    assert cfg2["poll_interval_sec"] == 360
    assert cfg2["screenshot_interval_sec"] == 900


def test_custom_values_preserved(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    p = config.config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("screenshot_interval_sec = 600\npoll_interval_sec = 60\nidle_after_sec = 180\n")
    cfg = config.load()
    assert cfg["poll_interval_sec"] == 60
    assert cfg["screenshot_interval_sec"] == 600


def test_per_key_independent_migration(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    p = config.config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("screenshot_interval_sec = 600\npoll_interval_sec = 5\nidle_after_sec = 180\n")
    cfg = config.load()
    assert cfg["poll_interval_sec"] == 360
    assert cfg["screenshot_interval_sec"] == 600


def test_corrupt_file_falls_back_to_sparse_defaults(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    p = config.config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x00\x01 not toml \xff\xfe")
    cfg = config.load()
    assert cfg["poll_interval_sec"] == 360
    assert cfg["screenshot_interval_sec"] == 900


def test_defaults_dict_is_sparse():
    assert config.DEFAULTS["poll_interval_sec"] == 360
    assert config.DEFAULTS["screenshot_interval_sec"] == 900
    assert config.DEFAULTS["idle_after_sec"] == 180
    assert 3600 / config.DEFAULTS["poll_interval_sec"] == 10
    assert 3600 / config.DEFAULTS["screenshot_interval_sec"] == 4
