# Observability

SkyPortal can expose OpenTelemetry request metrics in Prometheus format. It is
opt-in and off by default.

## Enabling metrics

In your `config.yaml`:

```yaml
observability:
  enabled: True
  service_name: skyportal
```

This instruments the Tornado app and serves metrics at `/api/internal/metrics`,
which requires a **System admin token** (scrape with `Authorization: token
<id>`). Each app worker serves its own metrics on its internal port
(`ports.app_internal + N`, default `65000..65003`); scrape those directly rather
than the nginx/public endpoint, which round-robins workers and returns partial
counters.

## Prometheus + Grafana

The `observability/` directory ships a ready-to-run stack: a scrape config,
Grafana provisioning, and a **SkyPortal Overview** dashboard. Copy
`observability/prometheus/skyportal_token.example` to `skyportal_token`, add a
System admin token, then start it alongside the app:

```bash
docker compose -f docker-compose.yaml \
  -f observability/docker-compose.observability.yaml up
```

Grafana is then at <http://localhost:3000> (admin/admin by default).
