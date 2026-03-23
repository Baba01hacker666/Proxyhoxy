import threading
import time
import urllib.request
import unittest
from proxy_server import PROXY_PORT, ThreadedHTTPServer, Proxy

class TestProxyServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use port 0 to let OS choose an available port
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), Proxy)
        cls.port = cls.server.server_address[1]
        
        def run_server():
            cls.server.serve_forever()
            
        cls.t = threading.Thread(target=run_server, daemon=True)
        cls.t.start()
        time.sleep(0.5)  # Wait for server to start

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.t.join(timeout=2)

    def test_proxy_starts(self):
        # Configure urllib to use our proxy
        proxy_handler = urllib.request.ProxyHandler({'http': f'http://127.0.0.1:{self.port}'})
        opener = urllib.request.build_opener(proxy_handler)
        
        try:
            resp = opener.open('http://httpbin.org/get', timeout=5)
            self.assertEqual(resp.getcode(), 200)
        except Exception as e:
            self.fail(f"Proxy request failed: {e}")

if __name__ == '__main__':
    unittest.main()
