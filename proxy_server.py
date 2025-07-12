# Proxyhoxy-main/proxy_server.py
import socket
import ssl
import http.server
import socketserver
import os
import configparser
import threading
import select
from datetime import datetime
from socketserver import ThreadingMixIn
from OpenSSL import crypto

# --- CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')

# Settings
settings = config['settings']
PROXY_PORT = settings.getint('proxy_port', 8080)
LOG_FILE = settings.get('log_file', 'datapassed.txt')
DOWNLOAD_FOLDER = settings.get('download_folder', 'downloads')
DOWNLOAD_EXTENSIONS = [ext.strip() for ext in settings.get('download_extensions', '').split(',')]

# MITM Settings
mitm_settings = config['mitm']
ENABLE_HTTPS_MITM = mitm_settings.getboolean('enable_https_mitm', False)

# Content Modification Settings
content_mod_settings = config['content_modification']
ENABLE_REPLACEMENT = content_mod_settings.getboolean('enable_replacement', False)
REPLACEMENTS = {k.encode(): v.encode() for k, v in content_mod_settings.items() if k != 'enable_replacement'}

# Certificate paths and cache
CERT_DIR = "certs"
CA_CERT_FILE = os.path.join(CERT_DIR, "ca.crt")
CA_KEY_FILE = os.path.join(CERT_DIR, "ca.key")
CERT_CACHE = {}
CERT_LOCK = threading.Lock()

# Ensure directories exist
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)


def get_cert_for_host(hostname):
    """Generates and caches a certificate for a given hostname, signed by our CA."""
    with CERT_LOCK:
        if hostname in CERT_CACHE:
            return CERT_CACHE[hostname]

        if not (os.path.exists(CA_CERT_FILE) and os.path.exists(CA_KEY_FILE)):
            raise FileNotFoundError("CA certificate/key not found. Please run generate_ca.py first.")

        # Load CA
        with open(CA_CERT_FILE, 'rb') as f:
            ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
        with open(CA_KEY_FILE, 'rb') as f:
            ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, f.read())

        # Generate cert
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
        
        cert = crypto.X509()
        cert.get_subject().CN = hostname
        cert.set_serial_number(int(datetime.now().timestamp() * 1000))
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365 * 24 * 60 * 60) # Valid for 1 year
        cert.set_issuer(ca_cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(ca_key, 'sha256')

        # Use temporary files for the SSL context
        cert_path = os.path.join(CERT_DIR, f".{hostname}.crt")
        key_path = os.path.join(CERT_DIR, f".{hostname}.key")
        
        with open(cert_path, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        with open(key_path, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

        CERT_CACHE[hostname] = (cert_path, key_path)
        return cert_path, key_path


class ThreadedHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""
    allow_reuse_address = True


class Proxy(http.server.BaseHTTPRequestHandler):
    """The main proxy handler class."""

    def do_GET(self, *args, **kwargs):
        """Handles HTTP GET requests."""
        if self.is_downloadable(self.path):
            self.log_request_details('GET', self.path)
            self.download_file()
        else:
            self.proxy_http_request()

    def do_POST(self, *args, **kwargs):
        """Handles HTTP POST requests."""
        self.proxy_http_request()

    def do_CONNECT(self):
        """Handles HTTPS CONNECT requests."""
        self.log_request_details('CONNECT', self.path)
        if ENABLE_HTTPS_MITM:
            self.mitm_https_connection()
        else:
            self.tunnel_connection()

    def proxy_http_request(self):
        """Proxies a standard, non-download HTTP request."""
        try:
            # Create a full URL
            url = f"http://{self.headers['Host']}{self.path}"
            
            # Prepare the request for urllib
            req_headers = {key: value for key, value in self.headers.items()}
            req = urllib.request.Request(url, headers=req_headers, method=self.command)
            
            if 'Content-Length' in self.headers:
                content_len = int(self.headers['Content-Length'])
                post_body = self.rfile.read(content_len)
                req.data = post_body

            with urllib.request.urlopen(req, timeout=10) as response:
                self.send_response(response.getcode())
                for key, value in response.getheaders():
                    self.send_header(key, value)
                self.end_headers()
                
                # Read and potentially modify the response
                content = response.read()
                modified_content = self.modify_content(content)
                self.wfile.write(modified_content)

        except Exception as e:
            self.send_error(502, f"Proxy Error: {e}")

    def mitm_https_connection(self):
        """Handles the full Man-in-the-Middle process."""
        try:
            hostname, port_str = self.path.split(':')
            port = int(port_str)
        except ValueError:
            self.send_error(400, "Bad CONNECT request")
            return
        
        try:
            cert_path, key_path = get_cert_for_host(hostname)
        except Exception as e:
            self.send_error(500, f"Could not generate certificate: {e}")
            return
        
        # 1. Respond to the client's CONNECT request
        self.send_response(200, "Connection Established")
        self.end_headers()

        # 2. Wrap the client socket with our generated cert to become an SSL server
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        try:
            ssl_client_socket = context.wrap_socket(self.connection, server_side=True)
        except ssl.SSLError as e:
            print(f"[-] SSL handshake error with client: {e}")
            return
        
        # 3. Connect to the real destination server as a standard SSL client
        try:
            dest_socket = socket.create_connection((hostname, port), timeout=10)
            ssl_dest_socket = ssl.create_default_context().wrap_socket(dest_socket, server_hostname=hostname)
        except Exception as e:
            print(f"[-] Could not connect to destination {hostname}: {e}")
            ssl_client_socket.shutdown(socket.SHUT_RDWR)
            ssl_client_socket.close()
            return

        # 4. Shuttle data between the client and the destination server
        self.shuttle_data(ssl_client_socket, ssl_dest_socket)

    def shuttle_data(self, client_socket, dest_socket):
        """Relays data between two sockets, allowing for modification."""
        sockets = [client_socket, dest_socket]
        try:
            while True:
                readable, _, exceptional = select.select(sockets, [], sockets, 10)
                if not readable and not exceptional:
                    break
                
                for sock in readable:
                    data = sock.recv(8192)
                    if not data: # Socket closed
                        return

                    if sock is client_socket:
                        # Data from client -> send to destination
                        dest_socket.sendall(data)
                    else: # sock is dest_socket
                        # Data from destination -> modify -> send to client
                        modified_data = self.modify_content(data)
                        client_socket.sendall(modified_data)

                if exceptional:
                    break
        except Exception as e:
            # print(f"Shuttle error: {e}") # Can be noisy
            pass
        finally:
            for sock in sockets:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()


    def modify_content(self, content: bytes) -> bytes:
        """Replaces keywords in text-based content if enabled."""
        if not (ENABLE_REPLACEMENT and REPLACEMENTS):
            return content
        
        # This is a simple replacement and may not work correctly on compressed
        # or chunked content. It's best for plain text like HTML/JS/CSS.
        for old, new in REPLACEMENTS.items():
            content = content.replace(old, new)
        return content

    def tunnel_connection(self):
        """A simple, non-intercepting tunnel for HTTPS."""
        # Same as the shuttle_data loop but without SSL or modification
        try:
            dest_host, dest_port = self.path.split(':')
            dest_port = int(dest_port)
            dest_socket = socket.create_connection((dest_host, dest_port), timeout=10)
            self.send_response(200, 'Connection Established')
            self.end_headers()
        except Exception as e:
            self.send_error(500, f"Failed to establish tunnel: {e}")
            return

        client_socket = self.connection
        client_socket.setblocking(False)
        dest_socket.setblocking(False)

        sockets = [client_socket, dest_socket]
        while True:
            try:
                readable, _, exceptional = select.select(sockets, [], sockets, 5)
                if not readable and not exceptional:
                    break
                
                for sock in readable:
                    data = sock.recv(8192)
                    if not data:
                        sockets.remove(sock)
                        continue
                    
                    if sock is client_socket:
                        dest_socket.sendall(data)
                    else:
                        client_socket.sendall(data)
                        
                if exceptional:
                    break
            except Exception:
                break
        
        client_socket.close()
        dest_socket.close()


    # --- Utility and Logging Methods ---

    def is_downloadable(self, path):
        """Checks if a URL path points to a file with a downloadable extension."""
        return any(path.lower().endswith(ext) for ext in DOWNLOAD_EXTENSIONS if ext)

    def download_file(self):
        """Downloads a file and saves it locally."""
        # This method would be similar to the improved version from the previous step
        # For brevity, it's omitted here but can be copied from the previous response.
        self.send_error(501, "Download functionality not shown in this version")

    def log_request_details(self, method, path):
        log_entry = (
            f"--- Request: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n"
            f"Client: {self.client_address[0]}\nMethod: {method}\nPath: {path}\n"
            f"--------------------------------------------------\n\n"
        )
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def log_message(self, format, *args):
        """Suppress default logging to stdout."""
        return

def main():
    """Sets up and runs the proxy server."""
    if ENABLE_HTTPS_MITM and not (os.path.exists(CA_CERT_FILE) and os.path.exists(CA_KEY_FILE)):
        print("[!!!] FATAL ERROR: MITM is enabled, but ca.crt or ca.key not found.")
        print("[!!!] Please run 'python3 generate_ca.py' first.")
        return

    try:
        server_address = ("", PROXY_PORT)
        httpd = ThreadedHTTPServer(server_address, Proxy)
        print(f"[*] Proxy server running on port {PROXY_PORT}...")
        if ENABLE_HTTPS_MITM:
            print("[*] HTTPS Man-in-the-Middle is ENABLED.")
        if ENABLE_REPLACEMENT:
            print("[*] Content replacement is ENABLED.")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server is shutting down.")
        httpd.shutdown()
    except Exception as e:
        print(f"[!] Could not start server: {e}")

if __name__ == "__main__":
    main()