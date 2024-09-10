import http.server
import socketserver
import os
from datetime import datetime

# Import shared data (ensure it's placed in the same directory as the proxy script)
from proxy_server.py import total_data_transferred, files_downloaded, last_request_time, proxy_start_time, log_file_path, download_folder

# Admin panel handler
class AdminPanelHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Serve the admin panel with proxy stats
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            uptime = datetime.now() - proxy_start_time
            last_request = last_request_time.strftime('%Y-%m-%d %H:%M:%S') if last_request_time else "No requests yet"

            html = f"""
            <html>
            <head><title>Proxy Admin Panel</title></head>
            <body>
                <h1>Proxy Admin Panel</h1>
                <p><strong>Uptime:</strong> {uptime}</p>
                <p><strong>Total Data Transferred:</strong> {total_data_transferred} bytes</p>
                <p><strong>Files Downloaded:</strong> {files_downloaded}</p>
                <p><strong>Last Request Time:</strong> {last_request}</p>
                <h2>Logs</h2>
                <p><a href="/logs">View Logs</a></p>
                <h2>Downloads</h2>
                <p><a href="/downloads">View Downloads</a></p>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))

        elif self.path == '/logs':
            # Serve the log file content
            if os.path.exists(log_file_path):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                with open(log_file_path, 'r') as log_file:
                    self.wfile.write(log_file.read().encode('utf-8'))
            else:
                self.send_error(404, "Log file not found")

        elif self.path == '/downloads':
            # Serve a list of downloaded files
            if os.path.exists(download_folder):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()

                files = os.listdir(download_folder)
                files_list = "".join([f"<li>{file}</li>" for file in files])

                html = f"""
                <html>
                <head><title>Downloads</title></head>
                <body>
                    <h1>Downloaded Files</h1>
                    <ul>{files_list}</ul>
                </body>
                </html>
                """
                self.wfile.write(html.encode('utf-8'))
            else:
                self.send_error(404, "Download folder not found")

        else:
            self.send_error(404, "Page not found")

# Function to start the admin panel server
def run_admin_panel(port=8081):
    with socketserver.TCPServer(("", port), AdminPanelHandler) as httpd:
        print(f"Admin panel running on port {port}")
        httpd.serve_forever()
