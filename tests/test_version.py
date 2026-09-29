from moon_tracker import ui, version


def test_get_version_format():
    v = version.get_version()
    assert isinstance(v, str) and v
    # inside the repo: "<branch>@<hash> <date>"; outside: "unknown"
    assert v == "unknown" or ("@" in v and len(v.split("@")[1].split()[0]) >= 7)


def test_get_version_fallback(monkeypatch):
    monkeypatch.setattr(version, "_git", lambda *a: None)
    assert version.get_version() == "unknown"


def test_version_footer_shows_runtime_version():
    assert ui.version_footer_text() == version.get_version()


def test_version_footer_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(version, "_git", lambda *a: None)
    assert ui.version_footer_text() == "unknown"
