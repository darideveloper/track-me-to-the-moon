# Browser domain capture (branch `web-extension`)

Feature documentation for work implemented on the **`web-extension`** branch.
The implementation is intentionally not on `main`; this document describes it so
`main` stays a working baseline while the feature is reviewed.

> Branch: `web-extension` (commit `5e1fe3a`)
> OpenSpec change: `openspec/changes/browser-extension-urls/`
> Install guide: `extension/README.md` (on the branch)

## What it adds

An Apploye-like team tracker currently records the foreground **app + window
title** every 5s. Titles are ambiguous ("GitHub") and Wayland blocks window
info. This feature adds the **active tab domain** (`github.com`, never paths or
query strings) collected by a browser extension and merged into each activity
row.

| Before | After (branch) |
|---|---|
| `app="Google Chrome", title="PR #42"` | `+ url="github.com"` |
| No browser signal | Domain per 5s activity row |
| Wayland: `(unavailable)` | Domains work regardless of window manager |

## Privacy model

Deliberately minimal, and this is the core of the design:

- **Domain only.** `https://github.com/acme/plan?token=abc` is reduced to
  `github.com` inside the browser; paths and query strings never leave the tab.
- **Private tabs** are recorded as the literal string `"(private)"` — visible
  that private browsing happened, not what was visited.
- **Internal pages** (`chrome://`, `edge://`, `about:`), empty URLs, and
  unfocused windows are skipped entirely.
- **No server, no account.** The extension only POSTs to the local tracker on
  `127.0.0.1`; nothing goes to a third party.

## How it works

```
Chrome / Edge / Brave / Firefox   (one MV3 extension, domain only)
        │  POST {domain, ts, browser}
        ▼  http://127.0.0.1:42813/url
┌────────────────────────────────────────────┐
│ moon_tracker (desktop)                     │
│  loopback listener (stdlib http.server)    │
│      └─▶ in-memory "last domain" (<=10s)   │
│  collector thread, every 5s:               │
│      if browser foreground + fresh + ON    │
│         └─▶ activities.url = domain        │
│  sync thread: POST /v1/activities (+ url)  │
└────────────────────────────────────────────┘
```

Extension events are pushed on tab activation, tab update, and window focus
change. The tracker holds the latest domain and attaches it to the next poll,
so there is no new table and no extra request per activity.

## Settings

A small **Record browser domains** toggle (default **on**) is added to the
settings screen, stored in `tracker.db` as `record_urls` (`"1"`/`"0"`). It is
read live by the collector, so it takes effect on the next poll without a
restart. When off, incoming extension events are acknowledged but ignored and
`url` stays empty. The toggle does **not** affect the existing Launch/Stop
settings validation.

## Backend contract

`POST /v1/activities` gains an **additive** `url` field (domain, `"(private)"`,
or `""`, ≤200 chars). Old clients that omit it must be accepted as `""`. The
backend contract document (`docs/backend-integration.md`) is updated on the
branch; servers should truncate to 200 chars and never return `4xx` for valid
rows (head-of-line blocking).

## Files on the branch

| Area | Path |
|---|---|
| Loopback listener | `src/moon_tracker/loopback.py` |
| Storage/migration | `src/moon_tracker/store.py` (`activities.url`, `record_urls`) |
| Collector wiring | `src/moon_tracker/app.py` |
| Sync payload | `src/moon_tracker/sync.py` |
| Settings toggle | `src/moon_tracker/ui.py` |
| Extension | `extension/` (`manifest.json`, `background.js`, `README.md`, `VERSION`) |
| Distributable | `extension.zip` |
| Tests | `tests/test_browser_urls.py`, `tests/test_store.py` |
| Backend contract | `docs/backend-integration.md` |

## Verification

- 39 tests pass (`pytest`); ruff `F`/`E9` checks clean.
- Loopback verified end-to-end: real HTTP `200` on valid POST, `400` on
  malformed, `404` on unknown path, bind-conflict degradation, sync marks
  uploaded.
- Live browser smoke test in Chrome/Edge/Brave/Firefox remains manual QA; steps
  are in `extension/README.md`.

## Out of scope

Full URLs and query strings, Safari/mobile, Web Store / AMO publishing,
enterprise force-install, and per-site allow/block lists.
