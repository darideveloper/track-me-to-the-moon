## Context

The tracker shipped as `worktracker`: default Flet styling, a green/grey PIL-drawn tray square, and a Start/Stop button pair. An explore-mode pass compared five moon-integration concepts (phase button, orbit progress, eclipse toggle, night-sky header, tray phases) and three palettes (Midnight Mission, Lunar Minimal, Nebula Playful). Decisions were locked interactively: **C×D Night-Sky Eclipse Bar + C×E coherence**, **Lunar Minimal with a Paper Moon light theme**, geometric generated icon, Launch/Land copy, and a full package rename with data migration. This document records the technical rationale behind the shipped implementation.

## Goals / Non-Goals

**Goals:**
- One memorable identity ("Track Me to the Moon") expressed in ≤3 widgets, readable from the taskbar.
- Dark/light theming with zero new runtime dependencies.
- Rename the installable to `moon-tracker` without losing a single existing session, setting, or screenshot.
- Single source of truth for recording/sync visuals across window, tray, and history.

**Non-Goals:**
- No custom painters or animation frameworks (orbit-progress concept deferred to v2).
- No change to tracking, sync, storage schema (one additive SELECT column excepted), or API contracts.
- No light-mode redesign of the header — the night sky stays dark in both modes as a brand anchor.

## Decisions

**C×D: pill toggle stacked under a night-sky header (not the C×A hero button).**
Two independent widgets, no coupling: a `Container` header plus a `Stack`-based pill (track label + sliding knob with `animate_position=300`). The hero button was deferred because it loses the familiar on/off affordance; the pill keeps toggle legibility while the header sells the brand. The shadow-slide animation code is reusable when growing toward C×A later.

**Lunar Minimal dark + Paper Moon light, SYSTEM default with manual override.**
Near-black/surface/white-text dark tokens plus a warm-paper light theme sharing one sky-blue accent (`#7DD3FC`). Implemented with stock `page.theme` / `page.dark_theme` (`color_scheme_seed`) and `ThemeMode.SYSTEM`; the override button cycles DARK→LIGHT only (two states, default system). Alternative (Midnight Mission gold) rejected: lower trust connotations for an employee-monitoring tool. Nebula gradient rejected: fights Flet defaults and readability.

**`brand.py` coherence module (C×E).**
All surfaces read `pending_total`, `sync_state`, `header_moon`, `row_moon`, `tray_title`, `page_themes`. Rationale: the tray previously spoke a different visual language (green square) than the window; one helper makes state legible from the taskbar with no extra UI to learn. Emoji moon glyphs (🌘/🌕) chosen over images for Flet views: zero asset pipeline, crisp at any size.

**Explicit light colors on fixed-dark surfaces.**
The header moon and knob glyphs initially inherited theme-default text color — invisible dark-on-navy in light mode. Fix: `color=MOON_WHITE` on any glyph sitting on a fixed dark background. Rule going forward: adaptive-background text uses defaults; fixed-background text pins its color.

**Geometric icon generated with Pillow (already a dependency).**
Crescent-on-disc + orbit ring at 512px, plus 256px and `.ico`; PyInstaller converts the PNG per-platform. No designer handoff, no new package. `.icns` not prebuilt — PyInstaller/Pillow handles macOS conversion at pack time.

**Rename to `moon_tracker` / `moon-tracker` with auto-migration and a compat alias.**
`git mv` preserves history. `config._migrate_dir` one-way-renames legacy `worktracker` dirs when the new ones are absent (never blocks startup on failure). A `worktracker` console-script alias remains so old habits keep working; `import worktracker` is intentionally dead. `list_sessions` gains an `uploaded` SELECT column (index-compatible, no schema migration) to drive per-row sync dots.

## Risks / Trade-offs

- [Risk] Migration runs once and renames directories — a crash mid-rename could strand data → Mitigation: `Path.rename` is atomic on the same filesystem; both dirs live under the same XDG base, and failure falls back to old behavior without blocking startup.
- [Risk] Emoji moon glyphs depend on system fonts; missing fonts fall back to monochrome → Mitigation: explicit light colors keep the fallback legible; shapes (crescent vs full) still read.
- [Risk] `page.window.icon` support varies by platform → Mitigation: guarded in try/except; icon is decoration and never breaks startup.
- [Trade-off] Single toggle replaces two buttons: first-time users may not read the pill as on/off → Mitigation: explicit "Tap to Launch/Land" caption plus Start/Stop tooltips.
- [Trade-off] `worktracker` script alias kept indefinitely → Mitigation: one line in pyproject; removal is a future BREAKING change if ever desired.

## Migration Plan

1. Deploy: `pip install -e .` (or new build) registers `moon-tracker` + `worktracker` scripts; first launch migrates legacy dirs and rebrands in place.
2. Rollback: reinstall the pre-rebrand build; legacy dirs were renamed, so restore `moon-tracker/*` → `worktracker/*` manually (manual reverse-rename; tracking behavior is unchanged so rollback is rarely needed).
3. No server-side changes; no DB migration (additive SELECT only).

## Open Questions

None outstanding. Deferred to v2: C×B orbit-progress ring, C×A hero-button growth, `.icns` prebuild verification on macOS hardware.
