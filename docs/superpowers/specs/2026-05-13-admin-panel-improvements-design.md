# Admin Panel Improvements Design

## Objective
Enhance the Proxyhoxy admin panel by adding a live configuration editor and upgrading the live traffic monitor to update dynamically without page reloads.

## Proposed Solution

### 1. Configuration & Keyword Editor
Currently, users must edit `config.ini` and restart the proxy to change settings or add new replacement keywords. 
- **UI additions:** A new `/config` route in `admin_panel.py` will render an HTML form populated with the current `config.ini` values. 
- **Form features:**
  - Toggles for `enable_https_mitm` and `enable_replacement`.
  - Text inputs for `proxy_port`, `admin_port`, `download_extensions`.
  - A dynamic list of keyword replacements where users can add new key-value pairs or delete existing ones.
- **Backend handling:**
  - A `POST` handler for `/config` will parse the submitted form data.
  - It will update the `config.ini` file using `configparser`.
  - Crucially, it will *also* dynamically update the live variables in `proxy_server.py` (`ENABLE_HTTPS_MITM`, `ENABLE_REPLACEMENT`, `REPLACEMENTS`, `DOWNLOAD_EXTENSIONS`) so that changes take effect immediately without a server restart.

### 2. Dynamic Live Traffic View
Currently, `/live` uses a javascript `setTimeout` to trigger a full page reload (`window.location.reload()`), causing screen flashes.
- **API Endpoint:** Create `/api/live` returning a JSON representation of `ACTIVE_REQUESTS`.
- **Frontend Script:** Modify the `/live` page HTML to include a vanilla JS script that uses `fetch('/api/live')` every 2 seconds. The script will clear the `<tbody>` and rebuild the rows dynamically, ensuring a smooth, modern experience.

## Scope
- Modify `admin_panel.py` to add new routes (`/config` GET/POST, `/api/live` GET) and the associated HTML templates.
- Ensure thread-safe updating of live configuration variables in `proxy_server.py`.

## Testing Strategy
- Start the proxy.
- Open the admin panel, navigate to "Configuration".
- Toggle "Enable Replacement" and add a new replacement keyword, then save.
- Verify `config.ini` is updated.
- Make an HTTPS request matching the new keyword and verify it is replaced immediately without proxy restart.
- Open the "Live Traffic" page and make requests; verify the table updates dynamically without the page flashing.