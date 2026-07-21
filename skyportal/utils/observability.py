import os

from baselayer.log import make_log

log = make_log("observability")

# Don't generate spans/metrics for the scrape endpoint or health-check noise.
_EXCLUDED_URLS = "/api/internal/metrics,/api/sysinfo"


def setup_observability(cfg):
    """Configure OpenTelemetry Tornado instrumentation and a Prometheus reader.

    Opt-in via the ``observability.enabled`` config key; a no-op otherwise, so
    default deployments are unaffected. Returns True when instrumentation was
    enabled, signalling the caller to register the ``/metrics`` route.
    """
    if not cfg.get("observability.enabled", False):
        return False

    # Must be set before the tornado instrumentation is imported, since it
    # reads the excluded-URL list at module import time.
    os.environ.setdefault("OTEL_PYTHON_TORNADO_EXCLUDED_URLS", _EXCLUDED_URLS)

    try:
        from opentelemetry import metrics
        from opentelemetry.exporter.prometheus import PrometheusMetricReader
        from opentelemetry.instrumentation.tornado import TornadoInstrumentor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    except ImportError:
        log("OpenTelemetry packages not installed; skipping observability setup")
        return False

    service_name = cfg.get("observability.service_name", "skyportal")
    resource = Resource.create({SERVICE_NAME: service_name})
    # PrometheusMetricReader registers a collector on prometheus_client's
    # default REGISTRY, which MetricsHandler then renders.
    reader = PrometheusMetricReader()
    metrics.set_meter_provider(
        MeterProvider(resource=resource, metric_readers=[reader])
    )

    TornadoInstrumentor().instrument()
    log(
        "OpenTelemetry instrumentation enabled; "
        "Prometheus metrics at /api/internal/metrics"
    )
    return True
