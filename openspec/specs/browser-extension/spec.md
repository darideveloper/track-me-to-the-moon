## Requirements

### Requirement: Single MV3 codebase for Chromium and Firefox

The extension SHALL ship one MV3 `manifest.json` (with `browser_specific_settings.gecko.id`, ignored by Chrome) and one `background.js` that works unpacked in Chromium-family browsers and Firefox.

#### Scenario: Active tab domain is reported on switch

- **WHEN** the user switches tabs or windows to an active `https://` page with a focused window
- **THEN** the extension POSTs `{"domain": "<hostname>", "ts": "<iso>", "browser": "<id>"}` to `http://127.0.0.1:42813/url`

#### Scenario: Internal pages are skipped

- **WHEN** the active tab URL is `chrome://`, `edge://`, `about:`, or empty
- **THEN** no POST is sent

#### Scenario: Minimal permissions

- **WHEN** the extension manifest is inspected
- **THEN** it requests only `permissions: ["tabs"]` plus `host_permissions: ["http://127.0.0.1:42813/*"]` and no `<all_urls>` or content scripts

### Requirement: Domain extraction and privacy marker

The extension SHALL derive the domain via hostname parsing (lowercased, full hostname with `www.` preserved, ≤200 chars) and substitute `"(private)"` for incognito contexts.

#### Scenario: Full URL is reduced to domain

- **WHEN** the active tab is `https://github.com/acme/plan?token=abc`
- **THEN** the POSTed domain is `github.com` with no path or query

#### Scenario: Incognito tab sends marker

- **WHEN** `tab.incognito` is true for the active tab
- **THEN** the extension POSTs domain `"(private)"` instead of the real hostname
