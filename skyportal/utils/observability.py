import os

from baselayer.log import make_log

log = make_log("observability")

# Don't generate spans/metrics for the scrape endpoint or health-check noise.
_EXCLUDED_URLS = "/api/internal/metrics,/api/sysinfo"

# Sampling cadence for the event-loop lag probe.
_LAG_PROBE_INTERVAL_MS = 500
# Module-level reference so the periodic callback isn't garbage-collected.
_lag_probe = None


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
    _instrument_event_loop_lag()
    log(
        "OpenTelemetry instrumentation enabled; "
        "Prometheus metrics at /api/internal/metrics"
    )
    return True


def _instrument_event_loop_lag():
    """Record how long the Tornado IOLoop is blocked between iterations.

    A callback scheduled every ``_LAG_PROBE_INTERVAL_MS`` should fire on that
    cadence; any extra delay is time the single-threaded loop spent blocked
    (e.g. in a synchronous handler). This is the most direct signal of async
    vs. blocking behavior. Recorded in milliseconds so the default histogram
    buckets resolve typical sub-second lag.
    """
    global _lag_probe
    from opentelemetry import metrics
    from tornado.ioloop import IOLoop, PeriodicCallback

    interval_s = _LAG_PROBE_INTERVAL_MS / 1000
    lag = metrics.get_meter("skyportal.observability").create_histogram(
        "tornado.event_loop.lag",
        unit="ms",
        description="Delay beyond the scheduled interval between IOLoop probe "
        "callbacks; nonzero means the loop was blocked.",
    )
    state = {"last": None}

    def probe():
        now = IOLoop.current().time()
        if state["last"] is not None:
            lag.record(max(0.0, (now - state["last"] - interval_s) * 1000))
        state["last"] = now

    _lag_probe = PeriodicCallback(probe, _LAG_PROBE_INTERVAL_MS)
    _lag_probe.start()
