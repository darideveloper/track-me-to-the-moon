## 1. Linux desktop helper

- [x] 1.1 Add `src/moon_tracker/desktop_entry.py` with pure helpers: app id (`moon-tracker`), entry/icon install paths, `.desktop` content rendering from a resolved repo root, and the platform→icon-filename map
- [x] 1.2 Implement `ensure_installed(repo_root)` (Linux-only): idempotent write of `moon-tracker.desktop` + hicolor PNG, best-effort `update-desktop-database` / `gtk-update-icon-cache`, skipped when `MOON_TRACKER_NO_DESKTOP_ENTRY=1`, all failures swallowed
- [x] 1.3 Implement `patch_client_icon()` (Linux-only): resolve the client via `flet_desktop.ensure_client_cached()` and copy `assets/moon-icon-256.png` → `<client>/flet/data/app_icon.png` when `data/` exists, best-effort

## 2. Startup wiring

- [x] 2.1 On Linux, in `ui.run()` before `ft.run(main)`: `os.environ.setdefault("FLET_APP_ID", "moon-tracker")`, then call the Linux helper chain only for GUI launches (not `--once`/`--shot`/`--version` paths); every step guarded so startup never breaks
- [x] 2.2 In `main()` (`ui.py`): select `page.window.icon` per platform — `assets/moon-icon.ico` on Windows, existing behavior elsewhere — keeping the try/except decoration guard

## 3. macOS best-effort

- [x] 3.1 On `sys.platform == "darwin"`: locate the cached client bundle via `flet_desktop.find_macos_app_bundle`, replace the recognized icon resource with `assets/moon-icon.icns` (backup first) only when the layout is recognized; silent skip otherwise
- [x] 3.2 Ensure `assets/moon-icon.icns` ships with the repo: generate it once (iconset + `sips`/`iconutil` on macOS, or PNG-element packing from `assets/moon-icon.png` elsewhere), commit the file, and document the regeneration command

## 4. Tests and docs

- [x] 4.1 Add one pytest covering the pure helpers: app id, install paths, entry content (id/`StartupWMClass`/`Icon` match), and the platform→icon-filename map
- [x] 4.2 Document in README: what auto-install writes, how to remove it, the `MOON_TRACKER_NO_DESKTOP_ENTRY=1` opt-out, that a future packaged install reuses the same app id and supersedes the dev entry, and the permanent packaging route (`flet build` `icon_linux.png`, `flet pack --icon` for Windows pins)

## 5. Verification

- [x] 5.1 Linux X11: `./run.sh`, confirm the panel taskbar entry shows the moon; `xprop -id <win> _NET_WM_ICON` reflects the new icon; rerun to confirm idempotency
- [x] 5.2 Linux Wayland: confirm the app-menu launcher shows the moon and starts the tracker; confirm CLI modes and the opt-out write nothing (running-window icon verified as packaging-only — see design decision 2)
- [x] 5.3 Windows: confirm the window uses `moon-icon.ico`; confirm the pinned-taskbar limitation note is accurate
- [x] 5.4 Run `uv run --frozen --extra dev pytest` green; `ruff` shows no new violation kinds vs the repo baseline (repo-wide EXE002 mode quirk + established best-effort `except` convention pre-date this change)
