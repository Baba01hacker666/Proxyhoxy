# MITM Data Corruption Fix Design

## Objective
Fix a critical bug in `Proxyhoxy` where the content replacement feature corrupts binary files (like images, archives) when downloaded over HTTPS connections. 

## Current Architecture & Flaw
Currently, when `ENABLE_HTTPS_MITM` and `ENABLE_REPLACEMENT` are true, `proxy_server.py` uses the `shuttle_data` method to pass raw decrypted bytes back and forth between the client and server. The method `self.modify_content(data)` is called on every chunk of data received from the server. This blindly replaces byte sequences matching the `config.ini` replacements, regardless of whether the chunk is part of an HTTP header, a text document, or a binary file. This corrupts binary files if they happen to contain bytes matching the target strings, and also breaks HTTP `Content-Length` guarantees.

## Proposed Solution
When an HTTPS connection is intercepted, we need to parse the decrypted traffic at the HTTP layer before modifying it, rather than modifying the raw TCP stream chunks.

1. **Selective Parsing:**
   - If `ENABLE_REPLACEMENT` is `false`, continue using the highly efficient `shuttle_data` raw socket tunnel.
   - If `ENABLE_REPLACEMENT` is `true`, we will not use `shuttle_data` for the server-to-client response. Instead, we will wrap the established TLS connection to the destination server using Python's `http.client` or manually parse the HTTP response stream.

2. **HTTP Aware Modification:**
   - Instead of raw tunneling, we will parse the HTTP response headers from the destination server.
   - We will inspect the `Content-Type` header.
   - If the `Content-Type` indicates text (e.g., `text/html`, `application/javascript`, `application/json`), we will read the entire response body, apply `modify_content`, recalculate the `Content-Length` header, and send the modified response to the client.
   - If the `Content-Type` indicates a binary format (or is missing), we will stream the response body to the client completely unmodified.

3. **Implementation Details:**
   - Refactor `mitm_https_connection` to route to a new `mitm_http_handler` if `ENABLE_REPLACEMENT` is true.
   - The `mitm_http_handler` will read the initial HTTP request from `ssl_client_socket` (which the client sends after the `CONNECT` tunnel is established), forward it to the `ssl_dest_socket`, and then read and parse the HTTP response from the server, applying selective modification based on headers before returning the data to the client.

## Scope
- Modify `proxy_server.py` (`mitm_https_connection`, `shuttle_data`, and add HTTP parsing logic for MITM).
- No changes required to `admin_panel.py` or the configuration schema.

## Testing Strategy
- Start the proxy with `ENABLE_HTTPS_MITM` and `ENABLE_REPLACEMENT` set to true.
- Request an HTTPS text page (e.g., `https://example.com`) and verify keywords are replaced.
- Request an HTTPS binary file (e.g., an image from `https://example.com/favicon.ico` or a zip file) and verify it downloads successfully without corruption.