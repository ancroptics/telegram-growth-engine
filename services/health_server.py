"""Health check server for UptimeRobot / Render."""
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import Config

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/health", "/", Config.HEALTH_CHECK_PATH):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress request logs


def start_health_server():
    """Start health check server in background thread."""
    port = Config.PORT + 1  # Use port+1 for health if main port is webhook
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Health server started on port {port}")
    except Exception as e:
        logger.warning(f"Health server failed to start: {e}")
