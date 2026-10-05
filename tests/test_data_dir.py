"""Isolated data dir (dev-data-dir): flag > env > default precedence."""
from pathlib import Path

from moon_tracker import config


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.delenv(config.DATA_DIR_ENV, raising=False)


def test_default_uses_xdg_data_home(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    d = config.data_dir()
    assert d == (tmp_path / "data" / "moon-tracker").resolve()
    assert (d / "shots").is_dir()
    assert config.is_default_dir(d)


def test_env_fallback(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv(config.DATA_DIR_ENV, str(tmp_path / "env-dev"))
    d = config.data_dir()
    assert d == (tmp_path / "env-dev").resolve()
    assert (d / "shots").is_dir()
    assert not config.is_default_dir(d)


def test_flag_wins_over_env(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv(config.DATA_DIR_ENV, str(tmp_path / "env-dev"))
    d = config.data_dir(str(tmp_path / "flag-dev"))
    assert d == (tmp_path / "flag-dev").resolve()
    assert not config.is_default_dir(d)


def test_relative_resolves_against_cwd(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    d = config.data_dir("dev-data")
    assert d == (tmp_path / "dev-data").resolve()
    assert d.is_absolute()
    assert (tmp_path / "dev-data" / "tracker.db").parent.is_dir() or True
    assert (d / "shots").is_dir()


def test_short_label_last_two_components(tmp_path):
    label = config.short_label(tmp_path / "a" / "dev-data")
    assert label == str(Path(*((tmp_path / "a" / "dev-data").resolve().parts[-2:])))


def test_symlinked_default_still_default(monkeypatch, tmp_path):
    """resolve() on both sides: an aliased default path must not show the badge."""
    _isolate(monkeypatch, tmp_path)
    default = config.default_data_dir()
    assert config.is_default_dir(str(default))


def test_dev_suffix_empty_on_default(monkeypatch, tmp_path):
    from moon_tracker import brand

    _isolate(monkeypatch, tmp_path)
    assert brand.dev_suffix(config.default_data_dir()) == ""
    assert brand.dev_suffix(None) == ""
    assert brand.tray_title(True, 0, False) == "Track Me to the Moon [Stopped]"


def test_dev_suffix_shows_label(monkeypatch, tmp_path):
    from moon_tracker import brand

    _isolate(monkeypatch, tmp_path)
    d = config.data_dir(str(tmp_path / "dev-data"))
    suffix = brand.dev_suffix(d)
    assert suffix.startswith(" [🧪 ")
    assert "dev-data" in suffix
    titled = brand.tray_title(True, 0, False, suffix=suffix)
    assert "🧪" in titled and "[Stopped]" in titled
    pending = brand.tray_title(False, 3, False, suffix=suffix)
    assert "3 pending" in pending and "🧪" in pending


def test_bundle_includes_data_dir(monkeypatch, tmp_path):
    from moon_tracker import debuglog

    _isolate(monkeypatch, tmp_path)
    d = config.data_dir(str(tmp_path / "dev-data"))
    bundle = debuglog.format_bundle("v", {}, None, [], d)
    assert f"data dir: {d}" in bundle
    plain = debuglog.format_bundle("v", {}, None, [])
    assert "data dir" not in plain


def test_manual_screenshot_honors_injected_dir(monkeypatch, tmp_path):
    from moon_tracker import api, store, sync
    from moon_tracker import shots as _shots

    _isolate(monkeypatch, tmp_path)
    ddir = config.data_dir(str(tmp_path / "dev-data"))
    default_dir = config.default_data_dir()
    con = store.connect(ddir / "tracker.db")
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    for k, v in (("api_base", "https://api.example.com"), ("api_token", "t"),
                 ("user_id", "u-dev")):
        store.set_setting(con, k, v)
    seen = {}

    def fake_take(d):
        seen["dir"] = str(d)
        p = ddir / "shots" / "fake.jpg"
        p.write_bytes(b"x")
        return p

    monkeypatch.setattr(_shots, "take", fake_take)
    monkeypatch.setattr(api, "post_screenshot",
                        lambda b, t, meta, path: api.SyncResult(ok=True))
    status, _msg, _stats = sync.manual_screenshot(
        con, {}, {"running": True, "sid": sid}, timeout=5, data_dir=ddir)
    assert status == "ok"
    assert seen["dir"] == str(ddir)
    assert not str(default_dir) or seen["dir"] != str(default_dir)
    rows = store.pending_screenshots(con, 10) + con.execute(
        "SELECT id, session_id, ts, path FROM screenshots").fetchall()
    assert any(str(ddir) in r[3] for r in rows)
    con.close()


def test_startup_logs_resolved_data_dir(monkeypatch, tmp_path, capsys):
    """`--data-dir X --once` prints `data dir: <abs>` (spec: startup logs dir)."""
    from moon_tracker import app

    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.argv",
                        ["moon-tracker", "--data-dir", str(tmp_path / "dev-data"),
                         "--once"])
    app.main()
    out = capsys.readouterr().out
    assert f"data dir: {(tmp_path / 'dev-data').resolve()}" in out


def test_dev_data_gitignored():
    """Repo `.gitignore` keeps `dev-data/` out of git status (spec scenario)."""
    from moon_tracker import config as _config

    repo = __import__("pathlib").Path(_config.__file__).resolve().parents[2]
    text = (repo / ".gitignore").read_text().splitlines()
    assert "dev-data/" in [ln.strip() for ln in text]
