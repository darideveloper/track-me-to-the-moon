"""Linux/macOS desktop identity: taskbar/dock icon for the Flet window.

Dev-mode Flet launches a prebuilt client whose window icon is its own
`data/app_icon.png` (X11 taskbars read it directly), while Wayland has no
window-icon concept and needs an installed `.desktop` entry matched by app id
(`FLET_APP_ID`). Everything here is best-effort: icon work is decoration and
never breaks startup.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_ID = "moon-tracker"
OPT_OUT_ENV = "MOON_TRACKER_NO_DESKTOP_ENTRY"
ICON_PNG = "moon-icon-256.png"


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def platform_icon_name(platform: str = sys.platform) -> str:
    """Asset filename for the window/taskbar identity per platform."""
    if platform == "win32":
        return "moon-icon.ico"
    if platform == "darwin":
        return "moon-icon.icns"
    return ICON_PNG


def entry_path(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".local" / "share" / "applications" / f"{APP_ID}.desktop"


def icon_path(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{APP_ID}.png"


def render_entry(exec_path: str, path: str) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name=Track Me to the Moon\n"
        f"Exec={exec_path}\n"
        f"Path={path}\n"
        f"Icon={APP_ID}\n"
        f"StartupWMClass={APP_ID}\n"
        "Categories=Utility;\n"
        "Terminal=false\n"
    )


def _write_if_changed(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_bytes() == data:
        return
    path.write_bytes(data)


def ensure_installed(root: str | Path | None = None, home: Path | None = None) -> bool:
    """Idempotent user-scope `.desktop` + icon install (Linux). Never raises."""
    if sys.platform != "linux" or os.environ.get(OPT_OUT_ENV) == "1":
        return False
    try:
        from . import brand

        root = Path(root or repo_root())
        _write_if_changed(entry_path(home), render_entry(str(root / "run.sh"), str(root)).encode())
        src = brand.asset_path(ICON_PNG)
        if src.is_file():
            _write_if_changed(icon_path(home), src.read_bytes())
        for cmd in (["update-desktop-database", str(entry_path(home).parent)],
                    ["gtk-update-icon-cache", "-f", "-t", str(icon_path(home).parent.parent.parent)]):
            try:
                subprocess.run(cmd, capture_output=True, timeout=15, check=False)
            except Exception:
                pass  # ponytail: cache refresh is cosmetic, tools may not exist
        return True
    except Exception:
        return False


def patch_client_icon() -> bool:
    """Copy the moon PNG over the cached Flet client's `data/app_icon.png` (Linux)."""
    if sys.platform != "linux":
        return False
    try:
        from flet_desktop import ensure_client_cached

        from . import brand

        dst = Path(ensure_client_cached()) / "flet" / "data" / "app_icon.png"
        if not dst.parent.is_dir():
            return False
        src = brand.asset_path(ICON_PNG)
        if not src.is_file():
            return False
        if dst.is_file() and dst.read_bytes() == src.read_bytes():
            return True
        shutil.copyfile(src, dst)
        return True
    except Exception:
        return False


def ensure_macos_bundle_icon() -> bool:
    """Replace the recognized icon in the cached Flet `.app` bundle (macOS)."""
    if sys.platform != "darwin":
        return False
    try:
        from flet_desktop import ensure_client_cached, find_macos_app_bundle

        from . import brand

        bundle = find_macos_app_bundle(ensure_client_cached())
        if not bundle:
            return False
        resources = Path(bundle) / "Contents" / "Resources"
        candidates = [resources / "app_icon.icns", *sorted(resources.glob("*.icns"))]
        target = next((c for c in candidates if c.is_file()), None)
        if target is None:
            return False
        src = brand.asset_path("moon-icon.icns")
        if not src.is_file():
            return False
        backup = target.with_suffix(".icns.flet-backup")
        if not backup.exists():
            shutil.copyfile(target, backup)
        if target.read_bytes() == src.read_bytes():
            return True
        shutil.copyfile(src, target)
        return True
    except Exception:
        return False
