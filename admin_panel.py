
---
### **`Proxyhoxy-main/admin_panel.py` (Updated)**

The admin panel now serves the CA certificate.

```python
# Proxyhoxy-main/admin_panel.py
import http.server
import os
import html
import configparser
from urllib.parse import unquote

# --- CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')

settings = config['settings']
LOG_FILE_PATH = settings.get('log_file', 'datapassed.txt')
EXT_FILE_PATH = settings.get('ext_log_file', 'extinon.txt')
DOWNLOAD_FOLDER = settings.get('download_folder', 'downloads')
ADMIN_PORT = settings.getint('admin_port', 5000)

CA_CERT_FILE = os.path.join("certs", "ca.crt")

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

class AdminHandler(http.server.SimpleHTTPRequestHandler):
    """
    Handles requests to the admin panel, serving logs, files, and the CA certificate.
    """
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.show_dashboard()
        elif self.path == '/files':
            self.show_files()
        elif self.path == '/logs':
            self.show_logs(LOG_FILE_PATH, "Proxy Logs")
        elif self.path == '/extensions':
            self.show_logs(EXT_FILE_PATH, "File Extensions Log")
        elif self.path == '/download-ca':
            self.serve_ca_cert()
        elif self.path.startswith('/download/'):
            self.handle_file_download()
        else:
            self.send_error(404, "File Not Found")

    def _serve_html(self, title, content):
        """Helper function to serve a standard HTML page."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{html.escape(title)}</title>
            <style> body {{ font-family: sans-serif; margin: 2em; }} pre {{ background-color: #f4f4f4; border: 1px solid #ddd; padding: 1em; white-space: pre-wrap; }} .ca-box {{ border: 2px dashed red; padding: 1em; margin-top: 1em; }}</style>
        </head>
        <body>
            <h1>{html.escape(title)}</h1>
            {content}
            <br><hr><a href='/'>Back to Dashboard</a>
        </body>
        </html>
        """
        self.wfile.write(html_content.encode('utf-8'))

    def show_dashboard(self):
        """Displays the admin dashboard."""
        ca_download_section = ""
        if os.path.exists(CA_CERT_FILE):
            ca_download_section = f"""
            <div class="ca-box">
                <h2>Download CA Certificate</h2>
                <p>To intercept HTTPS traffic, you must install this certificate in your browser.</p>
                <p><a href='/download-ca'>Download ca.crt</a></p>
            </div>
            """
        content = f"""
        <ul>
            <li><h2><a href='/logs'>View Request Logs</a></h2></li>
            <li><h2><a href='/extensions'>View File Extensions Log</a></h2></li>
            <li><h2><a href='/files'>Browse Downloaded Files</a></h2></li>
        </ul>
        {ca_download_section}
        """
        self._serve_html("Proxy Admin Panel", content)

    def serve_ca_cert(self):
        """Serves the CA certificate for download."""
        if not os.path.exists(CA_CERT_FILE):
            self.send_error(404, "CA Certificate not found. Run generate_ca.py first.")
            return
        
        self.send_response(200)
        self.send_header('Content-Disposition', 'attachment; filename="ca.crt"')
        self.send_header('Content-Type', 'application/x-x509-ca-cert')
        self.end_headers()
        with open(CA_CERT_FILE, 'rb') as f:
            self.wfile.write(f.read())
            
    # ... (other methods like show_logs, show_files, handle_file_download remain the same) ...
    def show_logs(self, file_path, title):
        """Displays the content of a given log file."""
        log_content = "<h3>No logs available.</h3>"
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as log_file:
                    log_content = f"<pre>{html.escape(log_file.read())}</pre>"
            except Exception as e:
                log_content = f"<h3>Error reading log file: {html.escape(str(e))}</h3>"
        self._serve_html(title, log_content)

    def show_files(self):
        """Lists files available for download."""
        content = "<h3>No files available for download.</h3>"
        if os.path.exists(DOWNLOAD_FOLDER) and os.listdir(DOWNLOAD_FOLDER):
            file_links = []
            for filename in os.listdir(DOWNLOAD_FOLDER):
                safe_name = html.escape(filename)
                file_links.append(f"<li><a href='/download/{safe_name}'>{safe_name}</a></li>")
            content = f"<ul>{''.join(file_links)}</ul>"
        self._serve_html("Downloadable Files", content)

    def handle_file_download(self):
        """Serves a requested file securely."""
        try:
            filename = os.path.basename(unquote(self.path[len('/download/'):]))
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
            if not os.path.abspath(file_path).startswith(os.path.abspath(DOWNLOAD_FOLDER)):
                self.send_error(403, "Forbidden")
                return
            if os.path.isfile(file_path):
                self.send_response(200)
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                self.send_header('Content-Type', 'application/octet-stream')
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File Not Found")
        except Exception as e:
            self.send_error(500, f"Server Error: {e}")

def run_server(port=ADMIN_PORT):
    """Starts the admin panel server."""
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, AdminHandler)
    print(f"Admin panel running on http://127.0.0.1:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()