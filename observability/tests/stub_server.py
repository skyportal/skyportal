"""Stand-in for SkyPortal's app workers in the observability smoke test.

Serves the same OpenTelemetry/Prometheus exposition the real app produces at
/api/internal/metrics, on the same internal ports (127.0.0.1:65000..65003), and
enforces the same `Authorization: token <id>` auth. Counts grow on each scrape
so rate()/histogram_quantile() panels return non-zero data. This lets the test
validate the real prometheus.yml, Grafana provisioning, and dashboard without
booting the full app image.
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXPECTED_TOKEN = os.environ.get("EXPECTED_TOKEN", "TESTTOKEN")
PORTS = [65000, 65001, 65002, 65003]
PATH = "/api/internal/metrics"

# (route, method, status, per-scrape count increment)
SERIES = [
    ("/api/sources", "GET", "200", 30),
    ("/api/config", "GET", "200", 12),
    ("/api/candidates", "GET", "401", 5),
    ("/api/sources", "POST", "500", 1),
]
BUCKETS = [5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
# cumulative fraction of requests at or below each bucket boundary
FRACS = [0.1, 0.3, 0.6, 0.8, 0.9, 0.95, 0.97, 0.99, 0.995, 0.999]

_state = {"n": 0}
_lock = threading.Lock()


def render(host):
    with _lock:
        _state["n"] += 1
        n = _state["n"]

    lines = ["# TYPE http_server_duration_milliseconds histogram"]
    for route, method, status, base in SERIES:
        total = base * n
        labels = (
            f'http_flavor="HTTP/1.1",http_host="{host}",http_method="{method}",'
            f'http_scheme="http",http_status_code="{status}",http_target="{route}"'
        )
        for le, frac in zip(BUCKETS, FRACS):
            lines.append(
                f"http_server_duration_milliseconds_bucket{{{labels},"
                f'le="{le}"}} {int(total * frac)}'
            )
        lines.append(
            f'http_server_duration_milliseconds_bucket{{{labels},le="+Inf"}} {total}'
        )
        lines.append(f"http_server_duration_milliseconds_sum{{{labels}}} {total * 40}")
        lines.append(f"http_server_duration_milliseconds_count{{{labels}}} {total}")

    lines.append("# TYPE http_server_active_requests gauge")
    lines.append(f'http_server_active_requests{{http_host="{host}"}} {1 + n % 3}')
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != PATH:
            self.send_response(404)
            self.end_headers()
            return
        if self.headers.get("Authorization", "") != f"token {EXPECTED_TOKEN}":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"unauthorized")
            return
        body = render(self.headers.get("Host", "localhost")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def serve(port):
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    for port in PORTS[:-1]:
        threading.Thread(target=serve, args=(port,), daemon=True).start()
    serve(PORTS[-1])
