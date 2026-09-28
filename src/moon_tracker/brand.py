"""Shared branding: display name, Lunar Minimal + Paper Moon tokens, eclipse helpers.

C×E coherence layer: window pill, tray icon, and history dots all read the
same helpers so recording/sync state speaks one visual language.
"""
from __future__ import annotations

from pathlib import Path

DISPLAY_NAME = "Track Me to the Moon"
PACKAGE_NAME = "moon_tracker"
DIST_NAME = "moon-tracker"

# Lunar Minimal (dark) + Paper Moon (light). Single sky accent in both.
DARK_BG = "#0E0E12"
DARK_SURFACE = "#1A1A20"
DARK_TEXT = "#F5F5F4"
DARK_MUTED = "#A1A1AA"
LIGHT_BG = "#FAFAF8"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_TEXT = "#18181B"
LIGHT_MUTED = "#71717A"
ACCENT_SKY = "#7DD3FC"
MOON_WHITE = "#E8E6DF"

# Night-sky header stays deep navy in both modes (brand anchor).
NIGHT_SKY = "#14141C"
NIGHT_STAR = "#3A3A4A"

# Moon glyphs (text, no image deps in Flet views).
MOON_STOPPED = "\U0001F318"  # 🌘 waning crescent
MOON_RECORDING = "\U0001F315"  # 🌕 full moon
MOON_SYNCED = MOON_RECORDING
MOON_PENDING = MOON_STOPPED

LAUNCH_LABEL = "Tap to Launch"
LAND_LABEL = "Tap to Land"
LAUNCH_TOOLTIP = "Start tracking"
LAND_TOOLTIP = "Stop tracking"


def asset_path(name: str = "moon-icon.png") -> Path:
    return Path(__file__).resolve().parent.parent.parent / "assets" / name


def pending_total(counts: dict) -> int:
    return int(counts.get("sessions", 0) + counts.get("activities", 0) + counts.get("screenshots", 0))


def sync_state(total_pending: int, last_error: str | None) -> str:
    """One of: pending | failed | synced | idle (shared by header, tray, history)."""
    if total_pending > 0:
        return "pending"
    if last_error:
        return "failed"
    if last_error is None:
        return "idle"
    return "synced"


def header_moon(running: bool) -> str:
    return MOON_RECORDING if running else MOON_STOPPED


def row_moon(uploaded: bool | None, any_pending: bool) -> str:
    """Per-row dot: uploaded flag when known, else global pending fallback."""
    if uploaded is True:
        return MOON_SYNCED
    if uploaded is False:
        return MOON_PENDING
    return MOON_PENDING if any_pending else MOON_SYNCED


def tray_title(stopped: bool, total_pending: int, synced: bool) -> str:
    base = f"{DISPLAY_NAME} [{'Stopped' if stopped else 'Recording'}]"
    if total_pending > 0:
        return f"{base} \u00b7 {total_pending} pending"
    if synced:
        return f"{base} \u00b7 synced"
    return base


def page_themes():
    """Return (light_theme, dark_theme) for Lunar Minimal + Paper Moon."""
    import flet as ft

    light = ft.Theme(color_scheme_seed=ACCENT_SKY)
    dark = ft.Theme(color_scheme_seed=ACCENT_SKY)
    return light, dark
