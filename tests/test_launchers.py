from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_launcher_preserves_diagnostic_arguments():
    launcher = (ROOT / "run.bat").read_text(encoding="utf-8")

    assert "MOON_TRACKER_DIAGNOSTIC" in launcher
    assert "--once" in launcher and "--shot" in launcher and "--version" in launcher
    assert "uv run --frozen python -m moon_tracker %*" in launcher


def test_linux_launcher_detaches_graphical_launches_and_logs_them():
    launcher = (ROOT / "run.sh").read_text(encoding="utf-8")

    assert "diagnostic=0" in launcher
    assert "--once|--shot|--version" in launcher
    assert "nohup setsid" in launcher
    assert "MOON_TRACKER_HIDDEN_LAUNCH" in launcher
    assert "launcher.log" in launcher
