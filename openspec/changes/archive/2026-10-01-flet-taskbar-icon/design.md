## Context

The tracker runs in dev via `run.sh` / `run.bat` → `python -m moon_tracker` → `ui.run()` → `ft.run(main)`. In dev mode Flet launches a prebuilt desktop client, not the app binary: on Linux the **light** client at `~/.flet/client/flet-desktop-light-<ver>/flet/flet`. Inspection of that launcher shows it loads `<client>/data/app_icon.png` (the Flet logo) and passes it to `gtk_window_set_default_icon`, which is what X11 taskbars render. The existing `page.window.icon = brand.asset_path()` (`ui.py:88`) is documented as Windows-only (`.ico`) and a no-op on Linux/macOS — confirmed in the installed Flet sources. Result: the Flet logo in the Linux taskbar despite `assets/moon-icon{,-256}.png` and `moon-icon.ico` shipping in the repo. Wayland has no window-icon concept at all (needs an installed `.desktop` entry matched by app id); macOS dev Dock icon comes from the prebuilt client bundle.

Beta status matters: there is no packaging/portable build yet (`tools/build.sh` is PyInstaller-only and unused for Flet), so the fix must live in the dev launch path. Contributors: Linux (X11/XFCE now, Wayland), Windows (untested), macOS (per user scope).

## Goals / Non-Goals

**Goals:**
- Moon icon in the taskbar/dock when the Flet window opens, on Linux X11, Linux Wayland, Windows, and macOS — from the `run.sh`/`run.bat` dev flow.
- Idempotent, user-scope-only side effects on Linux; icon work never breaks startup (existing "decoration" convention).
- One helper test; documented removal path and permanent packaging route.

**Non-Goals:**
- `flet pack` / `flet build` packaging, PyInstaller changes, and Windows pinned-taskbar (AppUserModelID/relaunch-icon) stamping — deferred, documented only.
- macOS robustness guarantee — best-effort, explicitly flagged.
- Passing `assets_dir` to `ft.run` (unrelated: `brand.asset_path()` reads the filesystem directly).
- New runtime dependencies; any change to tracking, sync, store, or settings behavior.

## Decisions

1. **Linux X11: patch the cached client's `data/app_icon.png` each launch.** The launcher hardcodes that path for `gtk_window_set_default_icon`, so it is the only dev-mode lever. Resolve the dir dynamically via `flet_desktop.ensure_client_cached()` (version/flavor-proof, no hardcoded paths) and copy `assets/moon-icon-256.png` before `ft.run`, wrapped in `try/except`.
   - Rejected: `FLET_VIEW_PATH` symlink shim (`/proc/self/exe` resolves the real binary, defeating it); runtime Xlib `_NET_WM_ICON` injection (racy, X11-only); `flet build linux` now (Flutter SDK, heavy for a dev fix).
2. **`FLET_APP_ID=moon-tracker` + auto-installed matching `.desktop` entry (Linux).** The entry gives a proper app-menu launcher with the moon icon and `FLET_APP_ID` names the process (visible in task managers). Verified limitation on flet-desktop-light-1.0.1: the prebuilt runner hardcodes `g_set_prgname("com.appveyor.flet")` and the GtkApplication `application-id`, so the id does **not** change WM_CLASS/app id and the entry cannot match the running window (Wayland running-icon needs a packaged build, which rebuilds the runner). Kept anyway: harmless, self-healing, and effective the moment a client honors it. Per user choice, install automatically into `~/.local/share/{applications,icons}` (idempotent rewrite, best-effort cache refresh, GUI-mode only, `MOON_TRACKER_NO_DESKTOP_ENTRY=1` opt-out).
3. **Windows: pass the existing `assets/moon-icon.ico` to `page.window.icon`.** The documented contract (`.ico`, Windows-only); the current PNG argument is invalid there. Pinned-group identity needs packaging → deferred non-goal.
4. **macOS: best-effort cached-bundle `.icns` patch.** In scope per user, but the client layout is unverified on this machine; patch is attempted only if the expected `app_icon.icns` exists, else skipped silently. Packaging with `.icns` remains the robust route.
5. **Placement and coupling.** New Linux helper in `src/moon_tracker/desktop_entry.py`, called from `ui.run()` (GUI path only); pure path/id helpers kept import-testable for the pytest. `flet_desktop` is a transitive dep of `flet` — no new dependency declared.

## Risks / Trade-offs

- [Risk] The client-cache patch is shared with other local Flet dev apps and reset on Flet upgrade/GC → Mitigation: re-applied every launch; documented.
- [Risk] macOS bundle layout differs → Mitigation: attempt-only-if-recognized, silent skip; flagged as the one uncertain item needing a macOS run.
- [Risk] Auto-install creates a dev menu entry and writes to `~/.local/share` → Mitigation: user scope, reversible, opt-out, exact paths + removal documented in README.
- [Risk] `ensure_client_cached()` may trigger a first-run download → Mitigation: same call Flet would make anyway; wrapped so failure never blocks startup.
