#!/usr/bin/env python3
"""Startup wrapper: health server -> wait for app -> TCP proxy"""

import http.server
import socketserver
import threading
import socket
import select
import subprocess
import os
import time
import sys

HEALTH_PORT = 8080
APP_PORT = 8081


# ── Phase 1: Immediate health response ───────────────────────────────────
class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass


httpd = socketserver.TCPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()
print(f"[init] Health endpoint OK on :{HEALTH_PORT}", flush=True)

# ── Phase 2: Launch real app ────────────────────────────────────────────
env = os.environ.copy()
env["PORT"] = str(APP_PORT)

proc = subprocess.Popen(
    ["bash", "/app/backend/start.sh"],
    env=env,
    cwd="/app/backend",
)

# ── Phase 3: Wait for app readiness ─────────────────────────────────────
for _ in range(90):  # 4.5 min ceiling
    time.sleep(3)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("localhost", APP_PORT))
        s.close()
        break
    except OSError:
        pass
else:
    print("[init] App failed to start – giving up", flush=True)
    proc.kill()
    sys.exit(1)

print(f"[init] App ready on :{APP_PORT}", flush=True)

# ── Phase 4: Swap health server for TCP proxy ───────────────────────────
httpd.shutdown()

proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
proxy.bind(("0.0.0.0", HEALTH_PORT))
proxy.listen(128)
print(f"[init] Proxy :{HEALTH_PORT} -> :{APP_PORT}", flush=True)


def forward(client, app_port=APP_PORT):
    """Simple TCP forwarder (one direction at a time)."""
    upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        upstream.connect(("localhost", app_port))
        client.setblocking(False)
        upstream.setblocking(False)

        while True:
            rlist, _, _ = select.select([client, upstream], [], [])
            if client in rlist:
                data = client.recv(65536)
                if not data:
                    break
                upstream.sendall(data)
            if upstream in rlist:
                data = upstream.recv(65536)
                if not data:
                    break
                client.sendall(data)
    except OSError:
        pass
    finally:
        client.close()
        upstream.close()


while True:
    c, addr = proxy.accept()
    threading.Thread(target=forward, args=(c,), daemon=True).start()
