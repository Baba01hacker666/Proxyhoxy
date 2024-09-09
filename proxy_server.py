import http.server
import socketserver
import urllib.request
import urllib.parse
import socket
import os
import select
from datetime import datetime
from socketserver import ThreadingMixIn
import threading

# Global variables to store proxy information
start_time = datetime.now()
total_data_transferred = 0
files_downloaded = 0
last_request_time = None
log_file_path = "datapassed.txt"
download_folder = "downloads"

# Ensure download folder exists
if not os.path.exists(download_folder):
    os.makedirs(download_folder)

# Multithreading support
class ThreadedHTTPServer(ThreadingMixIn, socketserver.TCPServer):
    """Handle requests in a separate thread."""
    pass

class Proxy(http.server.SimpleHTTPRequestHandler):
    download_extensions = ['.apk', '.zip', '.iso', '.rar', '.tar', '.7z', '.exe', '.bin']

    def log_connect_request(self, host, port):
        """Log the details of the CONNECT request."""
        global last_request_time
        client_ip = self.client_address[0]
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        last_request_time = current_time  # Update the last request time

        log_entry = (f"Date: {current_time}\n"
                     f"Client IP: {client_ip}\n"
                     f"Attempted CONNECT to: {host}:{port}\n"
                     f"=" * 40 + "\n")

        # Log to 'datapassed.txt'
        with open(log_file_path, 'a') as log_file:
            log_file.write(log_entry)

    def do_CONNECT(self):
        """Handle HTTPS requests via the CONNECT method."""
        global total_data_transferred
        try:
            # Parse host and port from the CONNECT request
            host, port = self.path.split(":")
            port = int(port)
            self.log_connect_request(host, port)

            # Establish a connection to the target server
            tunnel = socket.create_connection((host, port))
            self.send_response(200, "Connection Established")
            self.end_headers()

            # Tunnel the connection
            self._tunnel(tunnel)
        except Exception as e:
            self.send_error(500, f"Failed to establish tunnel: {e}")

    def _tunnel(self, tunnel):
        """Handle the tunnel communication."""
        global total_data_transferred
        self.connection.setblocking(False)
        tunnel.setblocking(False)
        inputs = [self.connection, tunnel]
        outputs = []

        try:
            while inputs:
                readable, writable, exceptional = select.select(inputs, outputs, inputs)

                for s in readable:
                    if s is self.connection:
                        client_data = self.connection.recv(4096)
                        total_data_transferred += len(client_data)  # Track data transferred
                        if client_data:
                            tunnel.sendall(client_data)
                        else:
                            inputs.remove(self.connection)
                            self.connection.close()
                    elif s is tunnel:
                        server_data = tunnel.recv(4096)
                        total_data_transferred += len(server_data)  # Track data transferred
                        if server_data:
                            self.connection.sendall(server_data)
                        else:
                            inputs.remove(tunnel)
                            tunnel.close()

                for s in exceptional:
                    inputs.remove(s)
                    s.close()

        except Exception as e:
            print(f"Tunnel error: {e}")

        finally:
            if self.connection:
                self.connection.close()
            if tunnel:
                tunnel.close()

    def do_GET(self):
        self.log_request_details()

    def do_POST(self):
        self.log_request_details()

    def log_request_details(self):
        global total_data_transferred, files_downloaded, last_request_time
        client_ip = self.client_address[0]
        requested_url = self.path
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        last_request_time = current_time  # Update the last request time

        try:
            parsed_url = urllib.parse.urlparse(requested_url)
            hostname = parsed_url.hostname
            if hostname is None:
                self.send_error(400, "Bad URL format")
                return

            server_ip = socket.gethostbyname(hostname)

            log_entry = (f"Date: {current_time}\n"
                         f"Client IP: {client_ip}\n"
                         f"Requested URL: {requested_url}\n"
                         f"Server IP: {server_ip}\n")

            # Check if the URL ends with a file extension that should be downloaded
            file_extension = self._get_file_extension_from_url(parsed_url.path)
            if file_extension:
                file_name = f"downloaded_file{file_extension}"

                # Forward the request and download the file
                url_to_fetch = f"{parsed_url.scheme}://{hostname}{parsed_url.path}"
                if parsed_url.query:
                    url_to_fetch += f"?{parsed_url.query}"

                with urllib.request.urlopen(url_to_fetch) as response:
                    save_file_in_current_directory(file_name, response.read())
                    files_downloaded += 1  # Track downloaded files

                    log_entry += f"File Downloaded: {file_name}\n"

            # Log the information
            log_entry += "=" * 40 + "\n"
            with open(log_file_path, 'a') as log_file:
                log_file.write(log_entry)

        except Exception as e:
            self.send_error(404, f"Error accessing {requested_url}: {e}")

    def _get_file_extension_from_url(self, path):
        """Check if the URL path ends with a valid download file extension."""
        for ext in self.download_extensions:
            if path.endswith(ext):
                return ext
        return None

def save_file_in_current_directory(file_name, file_data):
    """Save file in the current directory's download folder."""
    download_path = os.path.join(download_folder, file_name)
    with open(download_path, 'wb') as download_file:
        download_file.write(file_data)
    print(f"File saved to {download_path}")

def run_proxy_server(port=8080):
    handler = Proxy
    with ThreadedHTTPServer(("", port), handler) as httpd:
        print(f"Proxy server running on port {port}")
        httpd.serve_forever()

# Run the proxy server in a separate thread
proxy_thread = threading.Thread(target=run_proxy_server, args=(8080,))
proxy_thread.start()
