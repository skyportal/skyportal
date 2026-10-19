"""The analysis parameters SkyPortal reads itself, which no service declares."""

from skyportal.handlers.api.analysis import (
    RESERVED_ANALYSIS_PARAMETERS,
    unknown_analysis_parameters,
)
from skyportal.models.analysis import _insufficient_photometry

# FLARE_OSG's declared parameters, as the service carries them.
SERVICE_PARAMETERS = {
    "wrapper": ["flare"],
    "request_memory": {"type": "number", "default": 8192},
    "request_cpus": {"type": "number", "default": 1},
    "singularity_image": {"type": "string"},
}


def test_the_detection_gate_can_be_stored():
    # The gate reads these off default_analysis_parameters, so a service that
    # declares neither must still be able to hold them.
    params = {"wrapper": "flare", "request_memory": 8192, "min_detections": 8}
    assert unknown_analysis_parameters(params, SERVICE_PARAMETERS) == set()

    params["min_detections_per_filter"] = {"ztfg": 3}
    assert unknown_analysis_parameters(params, SERVICE_PARAMETERS) == set()


def test_a_key_no_one_declares_is_still_rejected():
    assert unknown_analysis_parameters(
        {"wrapper": "flare", "nonsense": 1}, SERVICE_PARAMETERS
    ) == {"nonsense"}


def test_the_reserved_keys_are_the_ones_the_gate_reads():
    # _insufficient_photometry reads these two; extinction correction reads the
    # third. Anything the core consumes itself belongs in the same set.
    assert {
        "min_detections",
        "min_detections_per_filter",
    } <= RESERVED_ANALYSIS_PARAMETERS
    assert "correct_extinction" in RESERVED_ANALYSIS_PARAMETERS


def test_an_analysis_without_the_gate_is_never_deferred():
    class _DefaultAnalysis:
        default_analysis_parameters = {"wrapper": "flare"}

    assert _insufficient_photometry(None, _DefaultAnalysis(), "ZTFtest") is False
