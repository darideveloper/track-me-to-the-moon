"""Screenshots with mss + Pillow: primary monitor, JPEG ~1280px/q60."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def take(data_dir: Path) -> Path | None:
    try:
        import mss
        from PIL import Image

        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        outdir = data_dir / "shots" / day
        outdir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%H-%M-%S")
        out = outdir / f"{ts}.jpg"

        with mss.mss() as sct:
            mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            raw = sct.grab(mon)
            img = Image.frombuffer("RGB", raw.size, raw.bgra, "raw", "BGRX")
            img.thumbnail((1280, 1280))
            img.save(out, "JPEG", quality=60)
        return out
    except Exception:
        return None  # e.g. Wayland denied / headless: skip silently, activity still logged
