## 1. Tracker storage + collector wiring

- [x] 1.1 Add `activities.url TEXT DEFAULT ''` migration in `store.py` (`_migrate` + `SCHEMA`), extend `add_activity(..., url="")` with `[:200]` truncation and `pending_activities` select
- [x] 1.2 Add `record_urls` to settings keys surface (DB-backed `"1"/"0"`, default `"1"`, strict validation, live-read each collector cycle; see `specs/settings-storage/spec.md` delta)
- [x] 1.3 Enrich collector in `app.py`: hold in-memory `last_domain{domain, ts, browser}`, attach when recording ON + foreground app is a known browser + event age ≤10s, else `""`

## 2. Loopback listener

- [x] 2.1 Create stdlib-only loopback module (`POST /url` on `127.0.0.1:42813`, 4KB cap, JSON `{domain, ts, browser}` validation, `400` on malformed, `ignored:true` when OFF, never bind `0.0.0.0`)
- [x] 2.2 Start listener as daemon thread in `start_background_threads`; bind failure logs warning and degrades to `url=""`
- [x] 2.3 Add/extend tests: migration backfill, truncation, stale-event cutoff, toggle OFF, malformed POST

## 3. Sync + docs

- [x] 3.1 Include additive `url` in `sync.py` activities items and update `api.py` typing/tests; keep chunking/ack order unchanged
- [x] 3.2 Update `docs/backend-integration.md` (§3.2 field table + example + §5.1 schema + §6 validation: accept missing/`""`/`"(private)"`, truncate 200, never 422 on valid rows)

## 4. Flet toggle button

- [x] 4.1 Add small URL-recording Switch/toggle to settings view (default ON), instant persist, live effect next poll, state survives restart
- [x] 4.2 Guard: toggle never bypasses existing Launch validation (`api_base`/`api_token`/`user_id`)

## 5. Browser extension (unpacked)

- [x] 5.1 Scaffold `extension/` (`manifest.json` MV3 + `gecko.id`, background-only `background.js`, no options page): `tabs.onActivated/onUpdated` + `windows.onFocusChanged`, focused-only, skip `chrome://`/`edge://`/`about:`, `permissions:["tabs"]` + `host_permissions:["http://127.0.0.1:42813/*"]`
- [x] 5.2 Domain extraction: `new URL().hostname` lowercase, `www.` preserved, ≤200 chars, `tab.incognito` → `"(private)"`, POST to `127.0.0.1:42813/url`
- [x] 5.3 Static smoke checks only (manifest MV3 + gecko.id asserts, `node --check background.js`, loopback bind-conflict degradation test) — live unpacked run in Chrome/Edge/Brave + Firefox is manual QA, steps in `extension/README.md`
- [x] 5.4 Write one-page internal install doc + versioned `extension.zip` (load-unpacked steps for `chrome://extensions` and `about:debugging`)

## 6. Verification

- [x] 6.1 Run `pytest`, `ruff`, and `--once` collector check; verify no new deps in `pyproject.toml`
- [x] 6.2 End-to-end: Launch → browse → Land → confirm `activities.url` domains in SQLite, synced items contain `url`, backend ack marks uploaded
