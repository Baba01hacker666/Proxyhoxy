import socket
import http.server
import socketserver
import urllib.request
import urllib.parse
import os
import select
from datetime import datetime
from socketserver import ThreadingMixIn

# Multithreading support
class ThreadedHTTPServer(ThreadingMixIn, socketserver.TCPServer):
    """Handle requests in a separate thread."""
    pass

class Proxy(http.server.SimpleHTTPRequestHandler):
    download_extensions = ['.apk', '.zip', '.iso', '.rar', '.tar', '.7z', '.exe', '.bin']

    def log_request_details(self, method):
        """Log details of HTTP requests and responses."""
        client_ip = self.client_address[0]
        requested_url = self.path
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            parsed_url = urllib.parse.urlparse(requested_url)
            hostname = parsed_url.hostname
            server_ip = socket.gethostbyname(hostname) if hostname else 'Unknown'

            log_entry = (
                f"--- Request Details ---\n"
                f"Date/Time: {current_time}\n"
                f"Client IP: {client_ip}\n"
                f"Method: {method}\n"
                f"Requested URL: {requested_url}\n"
                f"Server IP: {server_ip}\n"
                f"------------------------\n"
            )

            # Log to 'datapassed.txt'
            with open('datapassed.txt', 'a') as log_file:
                log_file.write(log_entry)

        except Exception as e:
            self.send_error(404, f"Error accessing {requested_url}: {e}")

    def log_file_extension(self, extension, requested_url):
        """Log details of viewed file extensions."""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        log_entry = (
            f"--- File Extension Viewed ---\n"
            f"Date/Time: {current_time}\n"
            f"Extension: {extension}\n"
            f"Requested URL: {requested_url}\n"
            f"------------------------------\n"
        )

        # Log to 'extinon.txt'
        with open('extinon.txt', 'a') as ext_file:
            ext_file.write(log_entry)

    def do_CONNECT(self):
        """Handle HTTPS requests via the CONNECT method."""
        try:
            host, port = self.path.split(":")
            port = int(port)
            self.log_request_details('CONNECT')

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
        self.connection.setblocking(False)
        tunnel.setblocking(False)
        inputs = [self.connection, tunnel]
        outputs = []
        message_queues = {}
        try:
            while inputs:
                readable, writable, exceptional = select.select(inputs, outputs, inputs)

                for s in readable:
                    if s is self.connection:
                        client_data = self.connection.recv(4096)
                        if client_data:
                            tunnel.sendall(client_data)
                        else:
                            # No more data from client, close the tunnel
                            inputs.remove(self.connection)
                            self.connection.close()
                    elif s is tunnel:
                        server_data = tunnel.recv(4096)
                        if server_data:
                            self.connection.sendall(server_data)
                        else:
                            # No more data from server, close the tunnel
                            inputs.remove(tunnel)
                            tunnel.close()

                for s in exceptional:
                    inputs.remove(s)
                    s.close()

        except Exception as e:
            print(f"Tunnel error: {e}")

        finally:
            # Ensure connections are closed
            if self.connection:
                self.connection.close()
            if tunnel:
                tunnel.close()

    def do_GET(self):
        self.log_request_details('GET')
        self.check_and_log_file_extension()

    def do_POST(self):
        self.log_request_details('POST')
        self.check_and_log_file_extension()

    def check_and_log_file_extension(self):
        """Check if the URL path ends with a valid file extension and log it."""
        parsed_url = urllib.parse.urlparse(self.path)
        file_extension = self._get_file_extension_from_url(parsed_url.path)
        if file_extension:
            self.log_file_extension(file_extension, self.path)

    def _get_file_extension_from_url(self, path):
        """Check if the URL path ends with a valid download file extension."""
        for ext in self.download_extensions:
            if path.endswith(ext):
                return ext
        return None

def save_file_in_current_directory(file_name, file_data):
    """Save the downloaded file to the current directory."""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    download_path = os.path.join(current_directory, file_name)

    with open(download_path, 'wb') as download_file:
        download_file.write(file_data)

    print(f"File saved to {download_path}")

def get_server_ip():
    """Get the IP address of the current server."""
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)

# Set up the server
PORT = 8080
handler = Proxy

with ThreadedHTTPServer(("", PORT), handler) as httpd:
    print(f"Proxy server running on IP: {get_server_ip()} on port {PORT}")
    httpd.serve_forever()
