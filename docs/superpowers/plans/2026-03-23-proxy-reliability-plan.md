# Proxy Reliability & Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the proxy server to use socket-level streaming instead of blocking `urllib` requests, improving performance and reliability.

**Architecture:** We will replace `urllib.request.urlopen` with raw TCP sockets. The `Proxy` class will parse the destination host from the headers or absolute path, connect to the destination, and pipe the data bidirectionally using `select.select`. If content modification is enabled, we'll parse the response with `http.client.HTTPResponse`.

**Tech Stack:** Python 3, `socket`, `select`, `http.client`, `ssl`

---

### Task 1: Setup Testing Environment

**Files:**
- Create: `test_proxy_server.py`

- [ ] **Step 1: Write a basic integration test**

```python
import threading
import time
import urllib.request
from proxy_server import PROXY_PORT, ThreadedHTTPServer, Proxy

def test_proxy_starts():
    server = ThreadedHTTPServer(("127.0.0.1", 0), Proxy)
    port = server.server_address[1]
    
    def run_server():
        server.serve_forever()
        
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    # Configure urllib to use our proxy
    proxy_handler = urllib.request.ProxyHandler({'http': f'http://127.0.0.1:{port}'})
    opener = urllib.request.build_opener(proxy_handler)
    
    try:
        resp = opener.open('http://httpbin.org/get', timeout=5)
        assert resp.getcode() == 200
    finally:
        server.shutdown()
        server.server_close()
```

- [ ] **Step 2: Run test to verify it passes with current code**
Run: `python3 -m unittest test_proxy_server.py`
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git add test_proxy_server.py
git commit -m "test: add basic proxy server integration test"
```

---

### Task 2: Implement Socket-Level Proxying for HTTP (do_GET/do_POST)

**Files:**
- Modify: `proxy_server.py` (Methods: `proxy_http_request`)

- [ ] **Step 1: Write the socket proxy logic**
Replace the `urllib` code in `proxy_http_request` with a socket implementation. Parse the `Host` header to get the destination IP and port (defaulting to 80). Connect a socket, reconstruct the HTTP request, send it, and call `self.shuttle_data(self.connection, dest_socket)`.

```python
    def proxy_http_request(self, req_id=None):
        try:
            # Parse destination from Host header or absolute path
            host_header = self.headers.get('Host', '')
            if not host_header:
                self.send_error(400, "Bad Request: No Host header")
                return

            if ':' in host_header:
                host, port = host_header.split(':', 1)
                port = int(port)
            else:
                host = host_header
                port = 80

            # Connect to destination
            dest_socket = socket.create_connection((host, port), timeout=10)

            # Reconstruct request
            # For HTTP proxy, the path is often absolute. Target expects relative or absolute.
            req_line = f"{self.command} {self.path} {self.request_version}\r\n"
            headers_str = "".join(f"{k}: {v}\r\n" for k, v in self.headers.items() if k.lower() != 'proxy-connection')
            request_data = (req_line + headers_str + "\r\n").encode('utf-8')
            
            dest_socket.sendall(request_data)

            # If there's a body, send it
            if 'Content-Length' in self.headers:
                content_len = int(self.headers['Content-Length'])
                req_body = self.rfile.read(content_len)
                dest_socket.sendall(req_body)

            # Use shuttle_data for streaming
            self.shuttle_data(self.connection, dest_socket, req_id=req_id)
            
            # Note: Content modification mode is omitted for brevity but should be handled if ENABLE_REPLACEMENT is True
        except Exception as e:
            self.send_error(502, f"Proxy Error: {e}")
```

- [ ] **Step 2: Run test to verify it still passes**
Run: `python3 -m unittest test_proxy_server.py`
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git add proxy_server.py
git commit -m "feat: replace urllib with socket streaming in proxy_http_request"
```

---

### Task 3: Handle Content Modification via http.client

**Files:**
- Modify: `proxy_server.py` (Method: `proxy_http_request`)

- [ ] **Step 1: Add modification fallback**
Update `proxy_http_request` to check `ENABLE_REPLACEMENT`. If True, use `http.client.HTTPConnection` to read the response, modify the body, and send it back, instead of using `shuttle_data`.

- [ ] **Step 2: Verify tests**
Run: `python3 -m unittest test_proxy_server.py`
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git add proxy_server.py
git commit -m "feat: handle content modification with http.client"
```

---

### Task 4: Enhance File Downloads (Stream to Disk and Client)

**Files:**
- Modify: `proxy_server.py` (Method: `download_file`)

- [ ] **Step 1: Rewrite `download_file`**
Replace `urllib` with a streaming socket connection. Read chunks from `dest_socket`, write to disk, and write to `self.connection` simultaneously.

- [ ] **Step 2: Run tests**
Run: `python3 -m unittest test_proxy_server.py`
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git add proxy_server.py
git commit -m "feat: stream downloads to disk and client simultaneously"
```

---

### Task 5: Improve Socket Stability in `shuttle_data` and `tunnel_connection`

**Files:**
- Modify: `proxy_server.py`

- [ ] **Step 1: Add exception handling to socket operations**
Catch `BlockingIOError`, `socket.timeout`, and `ConnectionResetError` during `recv` and `sendall`.

- [ ] **Step 2: Run tests**
Run: `python3 -m unittest test_proxy_server.py`
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git add proxy_server.py
git commit -m "fix: improve socket exception handling in streaming loops"
```