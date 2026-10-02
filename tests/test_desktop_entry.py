from moon_tracker import desktop_entry as de


def test_app_id():
    assert de.APP_ID == "moon-tracker"


def test_platform_icon_names():
    assert de.platform_icon_name("win32") == "moon-icon.ico"
    assert de.platform_icon_name("darwin") == "moon-icon.icns"
    assert de.platform_icon_name("linux") == "moon-icon-256.png"


def test_install_paths_match_app_id(tmp_path):
    assert de.entry_path(tmp_path).name == "moon-tracker.desktop"
    assert de.icon_path(tmp_path).name == "moon-tracker.png"


def test_rendered_entry_matches_app_id():
    entry = de.render_entry("/repo/run.sh", "/repo")
    assert "StartupWMClass=moon-tracker" in entry
    assert "Icon=moon-tracker" in entry
    assert "Exec=/repo/run.sh" in entry


def test_ensure_installed_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(de.sys, "platform", "linux")
    assert de.ensure_installed("/repo", tmp_path) is True
    entry, icon = de.entry_path(tmp_path), de.icon_path(tmp_path)
    assert entry.is_file() and icon.is_file()
    mtimes = (entry.stat().st_mtime_ns, icon.stat().st_mtime_ns)
    assert de.ensure_installed("/repo", tmp_path) is True
    assert (entry.stat().st_mtime_ns, icon.stat().st_mtime_ns) == mtimes


def test_ensure_installed_opt_out(tmp_path, monkeypatch):
    monkeypatch.setattr(de.sys, "platform", "linux")
    monkeypatch.setenv(de.OPT_OUT_ENV, "1")
    assert de.ensure_installed("/repo", tmp_path) is False
    assert not de.entry_path(tmp_path).exists()


def test_helpers_never_raise_off_linux(monkeypatch):
    monkeypatch.setattr(de.sys, "platform", "win32")
    assert de.ensure_installed() is False
    assert de.patch_client_icon() is False
    assert de.ensure_macos_bundle_icon() is False
    monkeypatch.setattr(de.sys, "platform", "darwin")
    assert de.ensure_installed() is False
    assert de.patch_client_icon() is False


def test_patch_client_icon_never_raises(tmp_path, monkeypatch):
    import flet_desktop

    monkeypatch.setattr(de.sys, "platform", "linux")

    def _boom():
        raise OSError("no client cache")

    monkeypatch.setattr(flet_desktop, "ensure_client_cached", _boom)
    assert de.patch_client_icon() is False
    monkeypatch.setattr(flet_desktop, "ensure_client_cached", lambda: str(tmp_path))
    assert de.patch_client_icon() is False  # no flet/data dir under client


def test_ensure_installed_survives_missing_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(de.sys, "platform", "linux")

    def _missing(*args, **kwargs):
        raise FileNotFoundError("no such tool")

    monkeypatch.setattr(de.subprocess, "run", _missing)
    assert de.ensure_installed("/repo", tmp_path) is True
    assert de.entry_path(tmp_path).is_file()
    assert de.icon_path(tmp_path).is_file()
