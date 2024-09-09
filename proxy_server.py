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

    def log_connect_request(self, host, port):
        """Log the details of the CONNECT request."""
        client_ip = self.client_address[0]
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        log_entry = (f"Date: {current_time}\n"
                     f"Client IP: {client_ip}\n"
                     f"Attempted CONNECT to: {host}:{port}\n"
                     f"=" * 40 + "\n")

        # Log to 'datapassed.txt'
        with open('datapassed.txt', 'a') as log_file:
            log_file.write(log_entry)
    
    def do_CONNECT(self):
        """Handle HTTPS requests via the CONNECT method."""
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
        self.log_request_details()

    def do_POST(self):
        self.log_request_details()

    def log_request_details(self):
        client_ip = self.client_address[0]
        requested_url = self.path
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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

                    # Log the download
                    log_entry += f"File Downloaded: {file_name}\n"

            # Log the information
            log_entry += "=" * 40 + "\n"
            with open('datapassed.txt', 'a') as log_file:
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
    # Get the current directory where the script is running
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Build the full path for saving the file
    download_path = os.path.join(current_directory, file_name)

    # Save the file in the current directory
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
