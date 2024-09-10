import http.server
import os
from urllib.parse import unquote
from datetime import datetime

LOG_FILE_PATH = "datapassed.txt"
EXT_FILE_PATH = "extinon.txt"
DOWNLOAD_FOLDER = "downloads"

# Ensure the directories exist
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

class AdminHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.show_dashboard()
        elif self.path == '/files':
            self.show_files()
        elif self.path == '/logs':
            self.show_logs()
        elif self.path == '/extensions':
            self.show_extensions()
        elif self.path.startswith('/download/'):
            self.handle_file_download()
        else:
            self.send_error(404, "File Not Found")

    def show_dashboard(self):
        """Display the admin dashboard with links to logs and files."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write(b"<html><head><title>Proxy Admin Panel</title></head><body>")
        self.wfile.write(b"<h1>Proxy Admin Panel</h1>")
        self.wfile.write(b"<h2><a href='/logs'>View Logs</a></h2>")
        self.wfile.write(b"<h2><a href='/extensions'>View Extensions Log</a></h2>")
        self.wfile.write(b"<h2><a href='/files'>Download Files</a></h2>")
        self.wfile.write(b"</body></html>")

    def show_logs(self):
        """Display the logs from datapassed.txt."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write(b"<html><head><title>Logs</title></head><body>")
        self.wfile.write(b"<h1>Proxy Logs</h1><pre>")

        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, 'r') as log_file:
                for line in log_file:
                    self.wfile.write(line.encode())
        else:
            self.wfile.write(b"No logs available.")

        self.wfile.write(b"</pre>")
        self.wfile.write(b"<a href='/'>Back to Dashboard</a>")
        self.wfile.write(b"</body></html>")

    def show_extensions(self):
        """Display the file extensions log from extinon.txt."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write(b"<html><head><title>File Extensions Log</title></head><body>")
        self.wfile.write(b"<h1>File Extensions Log</h1><pre>")

        if os.path.exists(EXT_FILE_PATH):
            with open(EXT_FILE_PATH, 'r') as ext_file:
                for line in ext_file:
                    self.wfile.write(line.encode())
        else:
            self.wfile.write(b"No file extensions log available.")

        self.wfile.write(b"</pre>")
        self.wfile.write(b"<a href='/'>Back to Dashboard</a>")
        self.wfile.write(b"</body></html>")

    def show_files(self):
        """List files available for download in the download folder."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write(b"<html><head><title>Download Files</title></head><body>")
        self.wfile.write(b"<h1>Downloadable Files</h1><ul>")

        if os.path.exists(DOWNLOAD_FOLDER):
            for filename in os.listdir(DOWNLOAD_FOLDER):
                file_url = f"/download/{filename}"
                self.wfile.write(f"<li><a href='{file_url}'>{filename}</a></li>".encode())
        else:
            self.wfile.write(b"No files available for download.")

        self.wfile.write(b"</ul>")
        self.wfile.write(b"<a href='/'>Back to Dashboard</a>")
        self.wfile.write(b"</body></html>")

    def handle_file_download(self):
        """Serve the file requested in the URL."""
        filename = unquote(self.path[len('/download/'):])
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)

        if os.path.exists(file_path):
            self.send_response(200)
            self.send_header('Content-Disposition', f'attachment; filename={filename}')
            self.send_header('Content-type', 'application/octet-stream')
            self.end_headers()

            with open(file_path, 'rb') as file:
                self.wfile.write(file.read())
        else:
            self.send_error(404, "File Not Found")

def run_server():
    PORT = 5000
    server_address = ('', PORT)
    httpd = http.server.HTTPServer(server_address, AdminHandler)
    print(f"Admin panel running on port {PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
