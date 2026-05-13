import http.server
import os
import html
import configparser
from urllib.parse import unquote
import base64
import json
import threading

config = configparser.ConfigParser()
config.read('config.ini')

settings = config['settings']
LOG_FILE_PATH = settings.get('log_file', 'datapassed.txt')
EXT_FILE_PATH = settings.get('ext_log_file', 'extinon.txt')
DOWNLOAD_FOLDER = settings.get('download_folder', 'downloads')
ADMIN_PORT = settings.getint('admin_port', 5000)
CA_CERT_FILE = os.path.join("certs", "ca.crt")
ADMIN_USER = settings.get('admin_user', 'admin')
ADMIN_PASS = settings.get('admin_password', 'changeme')

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Live traffic import (assume same process)
try:
    from proxy_server import ACTIVE_REQUESTS, ACTIVE_REQUESTS_LOCK
except ImportError:
    ACTIVE_REQUESTS = {}
    ACTIVE_REQUESTS_LOCK = threading.Lock()

def check_auth(header_value):
    if not header_value or not header_value.startswith("Basic "):
        return False
    try:
        auth_decoded = base64.b64decode(header_value.split(" ", 1)[1]).decode("utf-8")
        username, password = auth_decoded.split(":", 1)
        return username == ADMIN_USER and password == ADMIN_PASS
    except Exception:
        return False

class AdminHandler(http.server.SimpleHTTPRequestHandler):
    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Proxyhoxy Admin"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Authentication required.')

    def do_GET(self):
        auth_header = self.headers.get('Authorization')
        if not check_auth(auth_header):
            self.do_AUTHHEAD()
            return
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
        elif self.path == '/live':
            self.show_live_traffic()
        elif self.path == '/api/live':
            self.serve_live_api()
        else:
            self.send_error(404, "File Not Found")

    def serve_live_api(self):
        with ACTIVE_REQUESTS_LOCK:
            live_data = list(ACTIVE_REQUESTS.values())
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(live_data).encode('utf-8'))

    def _serve_html(self, title, content):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{html.escape(title)} - Proxyhoxy Admin</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-50 text-gray-800 font-sans min-h-screen">
            <nav class="bg-indigo-600 text-white shadow-md">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div class="flex items-center justify-between h-16">
                        <div class="flex items-center">
                            <span class="font-bold text-xl tracking-tight">Proxyhoxy Admin</span>
                        </div>
                        <div class="flex space-x-4">
                            <a href="/" class="hover:bg-indigo-500 px-3 py-2 rounded-md text-sm font-medium transition-colors">Dashboard</a>
                        </div>
                    </div>
                </div>
            </nav>
            <main class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
                <div class="bg-white shadow rounded-lg overflow-hidden">
                    <div class="px-4 py-5 border-b border-gray-200 sm:px-6">
                        <h1 class="text-2xl font-bold leading-6 text-gray-900">{html.escape(title)}</h1>
                    </div>
                    <div class="p-6">
                        {content}
                    </div>
                </div>
            </main>
        </body>
        </html>
        """
        self.wfile.write(html_content.encode('utf-8'))

    def show_dashboard(self):
        ca_download_section = ""
        if os.path.exists(CA_CERT_FILE):
            ca_download_section = f"""
            <div class="mt-8 bg-red-50 border-l-4 border-red-400 p-4 rounded-md">
                <div class="flex">
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Download CA Certificate</h3>
                        <div class="mt-2 text-sm text-red-700">
                            <p>To intercept HTTPS traffic, you must install this certificate in your browser.</p>
                        </div>
                        <div class="mt-4">
                            <a href='/download-ca' class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors">
                                Download ca.crt
                            </a>
                        </div>
                    </div>
                </div>
            </div>
            """
        content = f"""
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <a href='/logs' class="block p-6 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg shadow-sm transition-colors">
                <h2 class="text-xl font-semibold text-gray-900 mb-2">Request Logs</h2>
                <p class="text-gray-600">View detailed HTTP/HTTPS request history.</p>
            </a>
            <a href='/extensions' class="block p-6 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg shadow-sm transition-colors">
                <h2 class="text-xl font-semibold text-gray-900 mb-2">File Extensions Log</h2>
                <p class="text-gray-600">View logs of intercepted file extensions.</p>
            </a>
            <a href='/files' class="block p-6 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg shadow-sm transition-colors">
                <h2 class="text-xl font-semibold text-gray-900 mb-2">Downloaded Files</h2>
                <p class="text-gray-600">Browse and download intercepted files.</p>
            </a>
            <a href='/live' class="block p-6 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg shadow-sm transition-colors">
                <h2 class="text-xl font-semibold text-indigo-900 mb-2">Live Traffic</h2>
                <p class="text-indigo-700">Monitor active connections in real-time.</p>
            </a>
        </div>
        {ca_download_section}
        """
        self._serve_html("Dashboard", content)

    def serve_ca_cert(self):
        if not os.path.exists(CA_CERT_FILE):
            self.send_error(404, "CA Certificate not found. Run generate_ca.py first.")
            return
        self.send_response(200)
        self.send_header('Content-Disposition', 'attachment; filename="ca.crt"')
        self.send_header('Content-Type', 'application/x-x509-ca-cert')
        self.end_headers()
        with open(CA_CERT_FILE, 'rb') as f:
            self.wfile.write(f.read())

    def show_logs(self, file_path, title):
        log_content = "<div class='text-gray-500 italic'>No logs available.</div>"
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as log_file:
                    log_content = f"<pre class='bg-gray-900 text-gray-100 p-4 rounded-md overflow-x-auto text-sm font-mono'>{html.escape(log_file.read())}</pre>"
            except Exception as e:
                log_content = f"<div class='text-red-600 font-medium'>Error reading log file: {html.escape(str(e))}</div>"
        self._serve_html(title, log_content)

    def show_files(self):
        content = "<div class='text-gray-500 italic'>No files available for download.</div>"
        if os.path.exists(DOWNLOAD_FOLDER) and os.listdir(DOWNLOAD_FOLDER):
            file_links = []
            for filename in os.listdir(DOWNLOAD_FOLDER):
                safe_name = html.escape(filename)
                file_links.append(f"""
                <li class="py-3 sm:py-4">
                    <div class="flex items-center space-x-4">
                        <div class="flex-1 min-w-0">
                            <p class="text-sm font-medium text-gray-900 truncate">{safe_name}</p>
                        </div>
                        <div class="inline-flex items-center text-base font-semibold text-gray-900">
                            <a href='/download/{safe_name}' class="text-indigo-600 hover:text-indigo-900 text-sm">Download</a>
                        </div>
                    </div>
                </li>
                """)
            content = f"<ul class='divide-y divide-gray-200'>{''.join(file_links)}</ul>"
        self._serve_html("Intercepted Files", content)

    def handle_file_download(self):
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

    def show_live_traffic(self):
        table = """
        <div class="flex flex-col">
            <div class="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                <div class="py-2 align-middle inline-block min-w-full sm:px-6 lg:px-8">
                    <div class="shadow overflow-hidden border-b border-gray-200 sm:rounded-lg">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
                                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client IP</th>
                                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Method</th>
                                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Path</th>
                                </tr>
                            </thead>
                            <tbody id="live-table-body" class="bg-white divide-y divide-gray-200">
                                <tr><td colspan='4' class='px-6 py-4 text-center text-sm text-gray-500 italic'>Loading...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        <script>
        function escapeHtml(unsafe) {
            return (unsafe || '').toString()
                 .replace(/&/g, "&amp;")
                 .replace(/</g, "&lt;")
                 .replace(/>/g, "&gt;")
                 .replace(/"/g, "&quot;")
                 .replace(/'/g, "&#039;");
        }

        async function fetchLiveTraffic() {
            try {
                const response = await fetch('/api/live');
                const data = await response.json();
                const tbody = document.getElementById('live-table-body');
                
                if (data.length === 0) {
                    tbody.innerHTML = "<tr><td colspan='4' class='px-6 py-4 text-center text-sm text-gray-500 italic'>No active requests at the moment</td></tr>";
                    return;
                }
                
                tbody.innerHTML = data.map(r => `
                    <tr class='hover:bg-gray-50'>
                        <td class='px-6 py-4 whitespace-nowrap text-sm text-gray-500'>${escapeHtml(r.start)}</td>
                        <td class='px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900'>${escapeHtml(r.client_ip)}</td>
                        <td class='px-6 py-4 whitespace-nowrap text-sm text-gray-500'>
                            <span class='px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-indigo-100 text-indigo-800'>${escapeHtml(r.method)}</span>
                        </td>
                        <td class='px-6 py-4 text-sm text-gray-500 truncate max-w-xs' title='${escapeHtml(r.path)}'>${escapeHtml(r.path)}</td>
                    </tr>
                `).join('');
            } catch (err) {
                console.error("Failed to fetch live traffic", err);
            }
        }
        
        fetchLiveTraffic();
        setInterval(fetchLiveTraffic, 2000);
        </script>
        """
        self._serve_html("Live Traffic View", table)

def run_server(port=ADMIN_PORT):
    server_address = ('127.0.0.1', port)
    httpd = http.server.HTTPServer(server_address, AdminHandler)
    print(f"Admin panel running on http://127.0.0.1:{port} (username: {ADMIN_USER})")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
