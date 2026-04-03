"""Health check server for Render."""
import logging
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import Config

logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/health", "/", Config.HEALTH_CHECK_PATH):
            data = {"status": "running", "version": "v4.0.0"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def start_health_server():
    """Start health check server in background thread on PORT."""
    port = Config.PORT
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Health server started on port {port}")
    except Exception as e:
        logger.warning(f"Health server failed to start: {e}")
