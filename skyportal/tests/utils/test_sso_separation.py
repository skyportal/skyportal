"""The separation cut that decides whether a detection is photometry of a
solar system object, rather than of something near its predicted track.
"""

from skyportal.utils.sso_ingest import (
    MAX_SEPARATION_ARCSEC,
    is_on_target,
    point_separation,
)


def test_close_detections_are_kept():
    assert is_on_target({"ssdistnr": 0.0})
    assert is_on_target({"ssdistnr": 1.99})


def test_moderate_separations_are_kept():
    # An ephemeris good to only a few arcsec is still an ephemeris for this
    # object. Cutting here would discard most of a bad season's photometry.
    assert is_on_target({"ssdistnr": 5.0})
    assert is_on_target({"ssdistnr": 15.0})


def test_distant_detections_are_dropped():
    assert not is_on_target({"ssdistnr": MAX_SEPARATION_ARCSEC})
    # The contaminant population sits beyond the search radius' edge.
    assert not is_on_target({"ssdistnr": 22.0})
    assert not is_on_target({"ssdistnr": 30.0})


def test_negative_separation_is_a_no_match_marker():
    # The survey writes a negative distance to mean "no association", so it is
    # not a small separation and must not read as one.
    assert not is_on_target({"ssdistnr": -1.0})


def test_unrecorded_separation_is_kept():
    # Broker documents predating the field would otherwise be thinned silently.
    assert is_on_target({})
    assert is_on_target({"ssdistnr": None})
    assert is_on_target({"ssdistnr": "not a number"})


def test_normalized_key_wins_over_the_raw_survey_field():
    assert point_separation({"separation_arcsec": 3.0, "ssdistnr": 9.0}) == 3.0


def test_threshold_is_adjustable():
    assert is_on_target({"ssdistnr": 5.0}, max_arcsec=10.0)
    assert not is_on_target({"ssdistnr": 5.0}, max_arcsec=2.0)
