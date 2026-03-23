# Proxy Reliability & Performance Design

## Goal
Improve the proxy server's reliability, stability, and memory efficiency by transitioning from the blocking, memory-intensive `urllib` to raw socket-level stream proxying.

## Architecture & Data Flow
- **HTTP Proxy Handling**: In `do_GET` and `do_POST`, instead of fetching the entire response with `urllib`, we parse the destination host and port from the `Host` header (or from the absolute path). We establish a TCP connection directly to the destination server.
- **Raw Streaming**: The proxy reconstructs the HTTP request line and headers and sends them to the destination socket. It then uses the existing non-blocking `select` loop (`shuttle_data`) to pipe data bi-directionally between the client and the destination.
- **Benefits**: This prevents the proxy from buffering large files in memory, inherently supports Chunked Transfer Encoding, and seamlessly proxies protocols over HTTP (like WebSockets) without needing custom handlers.

## Modification Mode
- When `ENABLE_REPLACEMENT` is set in the configuration:
  - The proxy must parse the HTTP response before passing it to the client to apply text modifications.
  - To do this, the proxy will read headers from the socket using `http.client.HTTPResponse`, read the body, apply the configured string replacements, and then write the modified body back to the client.

## Intercepting Downloads
- When a file matches `DOWNLOAD_EXTENSIONS`, the `download_file` method is triggered.
- Instead of using `urllib` to download the entire file into memory before saving and serving it, the new implementation will connect via socket, parse the response, and iteratively read chunks.
- Each chunk will be simultaneously written to the local disk (in `DOWNLOAD_FOLDER`) and sent to the client's socket. This ensures no delay for the client and avoids out-of-memory errors for large files.

## Stability Enhancements
- **Socket Timeouts**: The `select` loop will enforce stricter idle timeouts to prevent dangling sockets.
- **Error Handling**: `EAGAIN`, `EWOULDBLOCK`, and general connection reset errors will be handled gracefully during the `recv`/`sendall` loop, cleanly shutting down and closing sockets.
- **Header Parsing Cleanup**: The proxy will properly distinguish between the absolute path (provided in the HTTP request line) and relative paths when forwarding requests to the target server.