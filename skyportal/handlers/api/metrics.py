from baselayer.app.access import permissions

from ..base import BaseHandler


class MetricsHandler(BaseHandler):
    """Expose OpenTelemetry-collected metrics in Prometheus text format.

    Served at ``/api/internal/metrics`` and registered only when
    ``observability.enabled`` is set. Requires a System admin token (scrape
    with ``Authorization: token <id>``). Each worker exposes its own metrics,
    so point Prometheus at the workers' internal ports directly rather than the
    load-balanced public endpoint.
    """

    @permissions(["System admin"])
    def get(self):
        """
        ---
        summary: Prometheus metrics
        description: |
          OpenTelemetry-collected request metrics in Prometheus text format.
          Requires a System admin token.
        tags:
          - system info
        responses:
          200:
            content:
              text/plain:
                schema:
                  type: string
        """
        # Imported lazily so the module loads even without the optional
        # prometheus-client dependency installed.
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        self.set_header("Content-Type", CONTENT_TYPE_LATEST)
        self.write(generate_latest())
