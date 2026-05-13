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

    def test_mitm_binary_replacement(self):
        import proxy_server
        import ssl
        
        # Save original settings
        old_mitm = proxy_server.ENABLE_HTTPS_MITM
        old_rep = proxy_server.ENABLE_REPLACEMENT
        old_reps = proxy_server.REPLACEMENTS
        
        try:
            # Enable MITM and Replacement
            proxy_server.ENABLE_HTTPS_MITM = True
            proxy_server.ENABLE_REPLACEMENT = True
            proxy_server.REPLACEMENTS = {b'bad': b'good'}
            
            # Disable SSL verification for the test client
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            proxy_handler = urllib.request.ProxyHandler({
                'http': f'http://127.0.0.1:{self.port}',
                'https': f'http://127.0.0.1:{self.port}'
            })
            opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
            
            # Request HTTPS endpoint with a header that will be reflected and replaced
            req = urllib.request.Request('https://httpbin.org/get')
            req.add_header('X-Test', 'bad')
            
            resp = opener.open(req, timeout=10)
            self.assertEqual(resp.getcode(), 200)
            
            print("Headers:", resp.headers)
            
            # Read data to ensure no corruption/exceptions during transfer
            data = resp.read()
            print("Received data:", data)
            self.assertTrue(len(data) > 0)
            
            # Verify data is valid JSON (not corrupted)
            import json
            json_data = json.loads(data.decode('utf-8'))
            self.assertEqual(json_data['url'], 'https://httpbin.org/get')
        except Exception as e:
            self.fail(f"MITM proxy request failed: {e}")
        finally:
            # Restore original settings
            proxy_server.ENABLE_HTTPS_MITM = old_mitm
            proxy_server.ENABLE_REPLACEMENT = old_rep
            proxy_server.REPLACEMENTS = old_reps

if __name__ == '__main__':
    unittest.main()
