## Why

Team leads need to know *which sites* time was spent on, not just window titles. Titles like "GitHub" don't distinguish work vs. distraction; domains do. The tracker is currently title-only by design, and Wayland already degrades window info — a browser extension bypasses the window manager entirely.

## What Changes

- Ship a single WebExtension codebase (MV3) for Chromium-family (Chrome, Edge, Brave, Chromium) + Firefox that POSTs the active tab **domain only** to the tracker on tab change / activation.
- Add a stdlib loopback listener in `moon_tracker` on fixed `127.0.0.1:42813` (`POST /url` with `{domain, ts, browser}`), no auth token (open localhost port, unpacked internal distribution).
- Enrich the next 5s `activities` row with the last-seen domain when the foreground app is a browser and the event is fresh (≤10s); incognito/private tabs send a `(private)` marker; otherwise `url` stays `""`.
- Add `activities.url` column (migration, ≤200 chars) and include `url` in `POST /v1/activities`; update `docs/backend-integration.md` accordingly. **BREAKING** payload addition (additive, old backends ignore unknown field; new backend must accept missing `url` from old clients).
- Add a small on/off **toggle button** for URL recording in the Flet settings screen (default ON), persisted and read live by the collector; when OFF the loopback is ignored and `url` stays `""`.
- Distribute the extension as an unpacked internal zip + docs (no Web Store / AMO publish in this change).

## Capabilities

### New Capabilities

- `browser-url-capture`: domain-only URL capture via extension + loopback enrichment + toggle + storage + sync of `activities.url`.
- `browser-extension`: the WebExtension source itself (manifest, background) for Chromium + Firefox — no options page (no token to configure).

### Modified Capabilities

- `background-sync`: `POST /v1/activities` items gain additive `url` field; drain order, batching, ack rules unchanged.
- `flet-ui`: settings view gains a URL-recording toggle button; existing timer/history behavior unchanged.
- `settings-storage`: settings keys gain `record_urls` (`"1"`/`"0"`, default `"1"`); live-read without restart applies to it as with existing keys.

## Impact

- Code: new `src/moon_tracker/loopback.py` + thread in `app.start_background_threads`; `store.py` schema/migration (`activities.url`); `collect.py`/`app.py` enrichment; `sync.py`/`api.py` payload; `ui.py` toggle; new `extension/` directory; `docs/backend-integration.md` update.
- No new PyPI dependencies (stdlib `http.server`); no new permissions for the desktop app (binds `127.0.0.1` only, never `0.0.0.0`).
- Backend team must accept/store optional `url` (domain, ≤200 chars, `"(private)"` or `""` legal values); out-of-scope: full URLs, query strings, Safari, store publishing, enterprise force-install.
