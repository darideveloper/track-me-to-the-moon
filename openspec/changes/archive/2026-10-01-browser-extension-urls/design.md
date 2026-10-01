## Context

`collect.poll()` (`src/moon_tracker/collect.py`) returns `(app, title)` only; `activities` rows carry `app ≤200 / title ≤500` and the backend contract (`docs/backend-integration.md §3.2`) states "never URLs". The collector thread (`app.start_background_threads`) polls every 5s; the sync thread drains sessions → activities → screenshots every 600s. Settings live in `tracker.db` (`store.SETTINGS_KEYS`); timing intervals live in `config.toml`. There is no localhost server and no `extension/` directory today.

Constraints from exploration: Win/Linux/Mac × Chromium-family + Firefox, unpacked internal distribution (no store publish), fixed port `42813`, open localhost (no token), domain-only, `(private)` marker for incognito, small toggle button (default ON), backend contract updated in the same change.

## Goals / Non-Goals

**Goals:**
- Capture active-tab **domain** (not full URL) with ≤10s freshness at the existing 5s activity cadence.
- One extension codebase for Chromium + Firefox (MV3), installable unpacked.
- Zero new PyPI deps; loopback binds `127.0.0.1` only.
- Toggle to disable URL recording without restarting; `url` column migrated, synced, documented.

**Non-Goals:**
- Full URLs, paths, query strings (explicitly excluded — privacy).
- Safari, mobile browsers, store publishing, enterprise force-install policies.
- Token auth for loopback, HTTPS loopback, per-site allow/block lists.

## Decisions

1. **Loopback HTTP POST over Native Messaging.** Native Messaging needs per-OS registry/dirs + a spawned host that must IPC back to the running tracker — breaks the PyInstaller onefile story. A stdlib `http.server` thread on `127.0.0.1:42813` is in-process, debuggable via `curl`, identical for all browsers/OS. Alternative rejected: WebSocket (no need for bidirectional push).
2. **Push + hold + enrich (not event log).** Extension POSTs `{domain, ts, browser}` on `tabs.onActivated / onUpdated / windows.onFocusChanged` (only when `tab.active && window.focused`); tracker keeps in-memory `last_domain{domain, ts, browser}` and the collector attaches it to the next activity row if `app` looks like a browser and `now - ts ≤ 10s`. Keeps the 5s cadence and avoids a new table. Alternative rejected: separate `browser_urls` table (more rows, join complexity, more privacy surface).
3. **Domain extraction in the extension.** `new URL(tab.url).hostname`, lowercased, full hostname kept as-is (`www.` preserved); `chrome://`, `about:`, `edge://`, empty → skip (no POST); `tab.incognito` → POST `"(private)"`. Query/path never leave the browser. Server re-validates length/charset and truncates to 200 chars.
4. **Open localhost, no token (accepted risk).** Unpacked-internal + domain-only makes spoofing impact low; saves a pairing step. Mitigation: bind `127.0.0.1` only, `POST /url` only, `Content-Length` cap (4KB), ignore non-JSON, no CORS wildcard needed beyond `127.0.0.1` (extension host permission covers it).
5. **Toggle stored in DB settings (`record_urls`, `"1"/"0"`, default `"1"`)**, read live by the collector each cycle (same pattern as `settings-storage` readers-observe-latest). Flet settings screen gets a small Switch/toggle button next to identity fields. When OFF: loopback POSTs are accepted but ignored (or return `{"ok":true,"ignored":true}`), and enrichment is skipped. Alternative rejected: `config.toml` key (requires restart to take effect, splits settings surfaces).
6. **Additive `url` field.** `activities.url TEXT DEFAULT ''`, backfilled `''`; `store.add_activity(..., url="")` param appended with default so old callers keep working; `pending_activities` selects `url`; sync builds `"url"` into items; backend truncates to 200 server-side and accepts `""` / `"(private)"` / missing (old clients). No backfill sync of old rows.

## Risks / Trade-offs

- [Risk] Any local process can POST fake domains (no token) → Mitigation: localhost-only, documented as v1 tradeoff; toggle lets users stop it; a token can be added later without payload change.
- [Risk] Two browsers open — last-write-wins could attach Chrome's domain to a Firefox poll → Mitigation: extension only sends when its window is focused; enrichment additionally requires foreground `app` to be a known browser and event age ≤10s.
- [Risk] `"(private)"` marker still reveals private-mode usage times → Mitigation: documented intent from exploration; toggle OFF covers users who want true invisibility.
- [Risk] Fixed port collision (another app on 42813) → Mitigation: bind failure logs a warning and URL capture degrades to `""`; activities/screenshots/sync unaffected; documented in troubleshooting.
- [Risk] Unpacked installs show dev-mode warnings and need manual updates → Mitigation: accepted for internal rollout; version the zip (`extension/VERSION`) and document re-install.

## Migration Plan

1. Ship tracker with `activities.url` migration (idempotent `ALTER TABLE`, same pattern as `store._migrate`), toggle default ON, loopback thread started alongside collector/sync threads.
2. Update `docs/backend-integration.md` + backend to accept optional `url` before clients upgrade (old clients omit it — must not 422).
3. Distribute `extension.zip` + one-page install doc (load unpacked, `chrome://extensions` / `about:debugging`); no DB backfill needed.
4. Rollback: toggle OFF or stop loopback thread → `url=""`; backend ignores the field; DB column stays (harmless).

## Open Questions

- Exact foreground-app name list treated as "browser" (Chrome, Edge, Brave, Firefox, Chromium, Opera, Vivaldi, Arc — case-insensitive substring match)?
- Should `POST /url` return the toggle state so the extension icon can grey out when OFF?
