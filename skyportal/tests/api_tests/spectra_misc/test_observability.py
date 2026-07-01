"""Unit tests for the opt-in OpenTelemetry observability setup.

These don't hit the live endpoint: /api/internal/metrics is nginx-blocked on
the public port and is only registered when ``observability.enabled`` is set
(off in the test server). The "enabled" path also mutates process-global OTel
state, so it is exercised in a subprocess to keep it out of the test session.
"""

import os
import subprocess
import sys
import textwrap

from skyportal.handlers.api.metrics import MetricsHandler
from skyportal.utils.observability import setup_observability


def test_observability_disabled_is_noop():
    # Missing key and explicit False both leave instrumentation off.
    assert setup_observability({}) is False
    assert setup_observability({"observability.enabled": False}) is False


def test_metrics_handler_requires_system_admin():
    # The @permissions decorator records the required ACL and marks the method
    # as authenticated; asserting on it confirms the gate is wired without a
    # running server.
    assert MetricsHandler.get.__permissions__ == ["System admin"]
    assert MetricsHandler.get.__authenticated__ is True


def test_observability_enabled_renders_prometheus():
    script = textwrap.dedent(
        """
        import os

        from skyportal.utils.observability import setup_observability

        cfg = {
            "observability.enabled": True,
            "observability.service_name": "skyportal-test",
        }
        assert setup_observability(cfg) is True

        # Our setup installs a real SDK meter provider (not the API's default
        # no-op), which is what makes metrics flow to the Prometheus reader.
        from opentelemetry import metrics
        from opentelemetry.sdk.metrics import MeterProvider

        assert isinstance(metrics.get_meter_provider(), MeterProvider)

        # ...and configures the tornado instrumentation to skip the scrape and
        # health URLs. This must be set before the instrumentation imports it.
        assert (
            os.environ["OTEL_PYTHON_TORNADO_EXCLUDED_URLS"]
            == "/api/internal/metrics,/api/sysinfo"
        )
        print("SUBPROCESS_OK")
        """
    )
    env = {
        **os.environ,
        "PYTHONPATH": os.getcwd() + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "SUBPROCESS_OK" in result.stdout
