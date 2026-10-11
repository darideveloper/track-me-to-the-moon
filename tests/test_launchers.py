from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_launcher_preserves_diagnostic_arguments():
    launcher = (ROOT / "run.bat").read_text(encoding="utf-8")

    assert "MOON_TRACKER_DIAGNOSTIC" in launcher
    assert "--once" in launcher and "--shot" in launcher and "--version" in launcher
    assert "run.vbs" in launcher
    assert "run.ps1" in launcher


def test_windows_hidden_launchers_are_autonomous_and_log_output():
    powershell = (ROOT / "run.ps1").read_text(encoding="utf-8")
    vbs = (ROOT / "run.vbs").read_text(encoding="utf-8")

    assert "Invoke-Uv" in powershell
    assert '"moon-tracker\\logs"' in powershell
    assert '"$sessionStamp.log"' in powershell
    assert "run.bat" not in powershell
    assert "-WindowStyle Hidden" in vbs
    assert "run.ps1" in vbs


def test_linux_launcher_detaches_graphical_launches_and_logs_them():
    launcher = (ROOT / "run.sh").read_text(encoding="utf-8")

    assert "diagnostic=0" in launcher
    assert "--once|--shot|--version" in launcher
    assert "nohup setsid" in launcher
    assert "MOON_TRACKER_HIDDEN_LAUNCH" in launcher
    assert "launcher.log" in launcher
