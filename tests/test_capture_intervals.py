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


def test_ui_scale_default_and_round_trip(monkeypatch, tmp_path):
    from moon_tracker import brand

    _isolate(monkeypatch, tmp_path)
    assert config.load()["ui_scale"] == 0.75
    cfg = config.load()
    cfg["ui_scale"] = 0.85
    config.save(cfg)
    assert config.load()["ui_scale"] == 0.85

    default = brand.UI_SCALE
    try:
        brand.set_scale(5)
        assert brand.UI_SCALE == 1.2
        brand.set_scale(0.1)
        assert brand.UI_SCALE == 0.6
        brand.set_scale("big")  # junk keeps the current scale
        assert brand.UI_SCALE == 0.6
    finally:
        brand.set_scale(default)
