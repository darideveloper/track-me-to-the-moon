## Why

Uploads are invisible: sync runs silently every 10 min and the UI shows only a one-line pending/failed/synced hint. When the backend rejects data (auth, schema, network) the user cannot see which endpoint failed, what was sent, or force a retry without quitting the app.

## What Changes

- Header debug entry (brand-matched bug icon) opening a full third debug view (same pattern as settings, not an overlay) alongside home and settings views.
- Manual actions available even when Stopped: Take screenshot now (attaches to active else most recent session, refuses when none exists; queue + immediate upload), per-type Send buttons (Sessions / Activities / Screenshots / Send all), Test connection ping (`GET /health` then empty sessions-probe fallback).
- Live API call log: in-memory ring of last 200 calls with compact rows (time + method + endpoint + item count + status + accepted/error) and tap-to-expand truncated JSON payload/response.
- Copy debug bundle (version + pending counts + last sync + last 20 log lines, token stripped) and Clear log actions.
- Auth token is never logged raw; only `auth: present/missing` is shown.

## Capabilities

### New Capabilities
- `debug-panel`: debug sheet UI, manual screenshot/send/test actions, in-memory API call log with expandable payloads, copy/clear bundle.

### Modified Capabilities
<!-- No existing spec requirements change; manual send reuses existing drain/ack semantics. -->

## Impact

- `src/moon_tracker/ui.py`: third view/sheet, header button, Flet-safe ticker rendering of log.
- `src/moon_tracker/api.py`: emit per-call events (endpoint, counts, status, truncated bodies) without changing `SyncResult` semantics.
- `src/moon_tracker/sync.py`: support `reason="manual"` + per-table filter for per-type sends; reused ack/marking logic.
- `src/moon_tracker/shots.py` / `store.py`: reused as-is (manual screenshot inserts via existing functions).
- No DB migration, no new dependencies, no backend contract change.
