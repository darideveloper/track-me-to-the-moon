## 1. Brand foundation (shipped)

- [x] 1.1 Create `src/moon_tracker/brand.py` with display name, Lunar Minimal + Paper Moon tokens, moon glyphs, and shared helpers (`pending_total`, `sync_state`, `header_moon`, `row_moon`, `tray_title`, `page_themes`)
- [x] 1.2 Generate `assets/moon-icon.png` (512px crescent-on-disc + orbit ring) plus 256px and `.ico` variants with Pillow
- [x] 1.3 Wire `--icon assets/moon-icon.png` and `--name moon-tracker` into `tools/build.sh`

## 2. Window rebrand (shipped)

- [x] 2.1 Set `page.title`, `page.theme`/`page.dark_theme` (`color_scheme_seed`), `ThemeMode.SYSTEM` default, manual override button, 340×560 window with icon (guarded)
- [x] 2.2 Build night-sky header `Container` (moon glyph, monospace timer, status, sync line, stars) with explicit light colors on all fixed-dark text
- [x] 2.3 Replace Start/Stop buttons with eclipse toggle (`Stack` track + knob, `animate_position=300`, Launch/Land captions + tooltips), keeping the settings gate
- [x] 2.4 Add history leading moon dots via `uploaded` column in `store.list_sessions`, plus the "tap the moon to launch" empty state
- [x] 2.5 Wrap settings fields in a `Card`; keep validation/save logic unchanged

## 3. Tray + notify rebrand (shipped)

- [x] 3.1 Asset-backed `_icon()` with sky ring when recording, legacy drawn fallback
- [x] 3.2 Tray titles via `brand.tray_title`, menu relabeled Launch/Land, branded toast strings in `notify.py`/`sync.py`

## 4. Module rename (shipped)

- [x] 4.1 `git mv src/worktracker` → `src/moon_tracker`; update test imports; rename dist to `moon-tracker` with `worktracker` script alias; `prog="moon-tracker"`
- [x] 4.2 Rename config/data dirs with `_migrate_dir` one-way legacy migration; update README quickstart/paths and package description
- [x] 4.3 Reinstall editable, full `pytest` green (32 passed), smoke-test entry points, dead old import, and migration

## 5. Verification (done)

- [x] 5.1 `py_compile` clean, `pytest tests/` 32 passed, brand/tray/migration smoke test green; ruff delta limited to the file's existing blind-except idiom
