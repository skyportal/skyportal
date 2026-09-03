"""Assertions for the observability smoke test.

Validates that the real kit artifacts work end to end against a running
Prometheus + Grafana (see docker-compose.test.yaml):
  - Prometheus scrapes the target successfully (proves prometheus.yml + token
    auth against the stub).
  - The emitted metrics are present.
  - Every PromQL expression in the shipped dashboard executes successfully, and
    the latency-histogram query returns data.
  - Grafana is healthy with the datasource and dashboard provisioned.
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DASHBOARD = os.path.join(HERE, "..", "grafana", "dashboards", "skyportal-overview.json")
PROM = "http://localhost:9090"
GRAFANA = "http://localhost:3000"
GRAFANA_AUTH = base64.b64encode(b"admin:admin").decode()


def get(url, auth=None, timeout=5):
    req = urllib.request.Request(url)
    if auth:
        req.add_header("Authorization", f"Basic {auth}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def poll(desc, fn, tries=60, delay=2):
    for _ in range(tries):
        try:
            if fn():
                print(f"OK: {desc}")
                return
        except (urllib.error.URLError, ConnectionError, json.JSONDecodeError):
            pass
        time.sleep(delay)
    sys.exit(f"FAIL: {desc}")


def prom_query(expr):
    url = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    return get(url)


def targets_up():
    d = get(f"{PROM}/api/v1/targets")
    active = d["data"]["activeTargets"]
    return sum(1 for t in active if t["health"] == "up") >= 1


def metric_present():
    d = prom_query("http_server_duration_milliseconds_count")
    return bool(d["data"]["result"])


def dashboard_exprs():
    with open(DASHBOARD) as f:
        dash = json.load(f)
    exprs = []
    for panel in dash["panels"]:
        for target in panel.get("targets", []):
            expr = target.get("expr")
            if expr:
                exprs.append((panel["title"], expr))
    return exprs


def grafana_healthy():
    return get(f"{GRAFANA}/api/health").get("database") == "ok"


def datasource_provisioned():
    ds = get(f"{GRAFANA}/api/datasources", auth=GRAFANA_AUTH)
    return any(d["type"] == "prometheus" for d in ds)


def dashboard_provisioned():
    res = get(
        f"{GRAFANA}/api/search?" + urllib.parse.urlencode({"query": "SkyPortal"}),
        auth=GRAFANA_AUTH,
    )
    return any("skyportal-overview" in d.get("uri", "") for d in res)


def main():
    # Grafana vars aren't understood by the Prometheus API; use a concrete range.
    def concrete(expr):
        return expr.replace("$__rate_interval", "1m").replace("$__interval", "1m")

    poll("prometheus target is up (scrape config + token auth)", targets_up)
    poll("emitted metric present in prometheus", metric_present)

    exprs = dashboard_exprs()
    for title, expr in exprs:
        d = prom_query(concrete(expr))
        if d.get("status") != "success":
            sys.exit(f"FAIL: dashboard query errored ({title}): {expr}\n{d}")
    print(f"OK: all {len(exprs)} dashboard queries execute")

    p95 = "histogram_quantile(0.95, sum(rate(http_server_duration_milliseconds_bucket[1m])) by (le))"
    poll(
        "latency histogram query returns data",
        lambda: bool(prom_query(p95)["data"]["result"]),
    )

    poll("grafana healthy", grafana_healthy)
    poll("grafana datasource provisioned", datasource_provisioned)
    poll("grafana dashboard provisioned", dashboard_provisioned)

    print("\nAll observability smoke checks passed.")


if __name__ == "__main__":
    main()
