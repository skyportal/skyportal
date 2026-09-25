"""Measuring a moving-object track from its difference cutouts.

The failure this guards against is silent: a standard-deviation background
demotes real detections to noise and reports nothing unusual while doing it.
"""

import json
import pathlib

import numpy as np
import pytest

from skyportal.utils.moving_object_track import (
    NotMeasurable,
    background,
    band_flux_agreements,
    band_flux_is_consistent,
    measure_cutout,
    motion_residuals,
    position_angles,
    stretch_limits,
)

FIXTURE = pathlib.Path(__file__).parents[3] / "data" / "asteroid_track_fixture.json"


def stamp(peak=200.0, noise=5.0, size=63, offset=(0, 0), seed=0):
    """A 63x63 difference stamp with a point source at (or near) the centre."""
    rng = np.random.default_rng(seed)
    data = rng.normal(0.0, noise, (size, size))
    centre = size // 2
    data[centre + offset[0], centre + offset[1]] += peak
    return data


def test_a_centred_source_is_measured_at_the_centre():
    result = measure_cutout(stamp())
    assert result["centroid_offset_px"] == 0.0
    assert result["snr"] > 10


def test_an_offset_source_reports_its_offset():
    assert measure_cutout(stamp(offset=(0, 2)))["centroid_offset_px"] == 2.0


def test_a_brighter_source_is_more_significant():
    faint = measure_cutout(stamp(peak=50.0))["snr"]
    bright = measure_cutout(stamp(peak=400.0))["snr"]
    assert bright > faint


def ring_pixels(data, inner=12, outer=25):
    yy, xx = np.mgrid[0 : data.shape[0], 0 : data.shape[1]]
    centre = data.shape[0] // 2
    radius = np.hypot(yy - centre, xx - centre)
    return data[(radius > inner) & (radius < outer)]


def test_a_field_star_in_the_annulus_does_not_hide_the_source():
    # The whole point of the MAD: a star in the background ring inflates a
    # standard deviation enough to push a real detection under 3 sigma.
    data = stamp(peak=120.0, noise=5.0)
    data[31, 31 + 18] += 3000.0

    _, sigma_mad = background(data)
    sigma_std = float(np.std(ring_pixels(data)))

    assert sigma_mad < sigma_std / 5, "a std sigma is inflated by the field star"
    assert measure_cutout(data)["snr"] > 10, "the MAD sigma still sees the source"

    naive_snr = measure_cutout(data)["peak"] / sigma_std
    assert naive_snr < 3, "the naive implementation is what loses the detection"


def test_a_flat_stamp_is_refused_rather_than_divided_by_zero():
    with pytest.raises(NotMeasurable, match="flat"):
        measure_cutout(np.zeros((63, 63)))


def test_a_stamp_too_small_for_the_annulus_is_refused():
    with pytest.raises(NotMeasurable, match="background pixels"):
        measure_cutout(stamp(size=7))


def test_nans_do_not_poison_the_measurement():
    data = stamp()
    data[0, 0] = np.nan
    assert np.isfinite(measure_cutout(data)["snr"])


def test_the_annulus_matches_the_brief_on_a_ztf_stamp():
    # 12-25 px on a 63x63 cutout is what the hand analysis measured against.
    from skyportal.utils.moving_object_track import (
        ANNULUS_INNER_FRACTION,
        ANNULUS_OUTER_FRACTION,
    )

    centre = 63 // 2
    assert round(centre * ANNULUS_INNER_FRACTION) == 12
    assert round(centre * ANNULUS_OUTER_FRACTION) == 25


def test_a_stamp_of_another_size_still_measures():
    # The ring scales with the stamp, so nothing needs a plate scale per survey.
    assert np.isfinite(measure_cutout(stamp(size=127))["snr"])


def test_the_stretch_is_keyed_to_the_background():
    low, high = stretch_limits(10.0, 2.0)
    assert (low, high) == (6.0, 28.0)


def detection(jd, ra, dec, band="r", mag=20.0, peak=100.0):
    return {"jd": jd, "ra": ra, "dec": dec, "band": band, "mag": mag, "peak": peak}


def test_position_angle_turns_along_a_curving_arc():
    arc = [
        detection(2461293 + i, 9.0 - 0.12 * i, 48.6 + 0.10 * i - 0.002 * i * i)
        for i in range(8)
    ]
    angles = position_angles(arc)
    assert len(angles) == 7
    assert angles[0] > angles[-1], "the angle should rotate along the arc"


def test_a_short_arc_drops_the_degree_rather_than_overfitting():
    # Two or three nights is the case that matters for a fast-moving object,
    # and a cubic through four points has no freedom left to show a residual.
    arc = [detection(2461293 + i, 9.0 - 0.1 * i, 48.6 + 0.1 * i) for i in range(5)]
    result = motion_residuals(arc, degree=3)
    assert result["degree"] == 2
    assert result["n_points"] == 5


def test_too_few_points_to_fit_reports_nothing():
    arc = [detection(2461293 + i, 9.0 - 0.1 * i, 48.6 + 0.1 * i) for i in range(3)]
    assert motion_residuals(arc) is None


def test_a_straight_track_has_a_small_residual():
    arc = [detection(2461293 + i, 9.0 - 0.1 * i, 48.6) for i in range(8)]
    assert motion_residuals(arc)["rms_arcsec"] < 0.01


def test_band_pairs_too_close_in_magnitude_are_skipped():
    # r=19.60 against i=19.59 is the same measurement twice; which is brighter
    # in the pixels says nothing, and counting it would fail a real track.
    pair = [
        detection(2461293.30, 9.0, 48.6, "r", mag=19.60, peak=80),
        detection(2461293.36, 9.0, 48.6, "i", mag=19.59, peak=34),
    ]
    assert band_flux_agreements(pair) == []
    assert band_flux_is_consistent(pair) is True


def test_bands_on_different_nights_are_not_compared():
    # Peak counts are only comparable under one night's seeing and sky.
    pair = [
        detection(2461293.3, 9.0, 48.6, "g", mag=20.1, peak=50),
        detection(2461296.3, 9.0, 48.6, "r", mag=19.7, peak=20),
    ]
    assert band_flux_agreements(pair) == []


def test_a_disagreeing_same_night_pair_is_caught():
    pair = [
        detection(2461293.30, 9.0, 48.6, "g", mag=20.14, peak=93),
        detection(2461293.36, 9.0, 48.6, "r", mag=19.71, peak=54),
    ]
    assert band_flux_is_consistent(pair) is False


# A real BOOM cluster that crosses 0h: raw RA arithmetic read the last epoch as
# a 360 degree jump and reported a 253072 arcsec residual on a good track.
CROSSES_ZERO = [
    detection(2461301.85050, 0.343439, -4.038348),
    detection(2461301.86233, 0.340963, -4.039613),
    detection(2461302.75772, 0.172060, -4.128502),
    detection(2461303.83336, 359.964978, -4.234539),
]


def test_a_track_crossing_zero_hours_is_fitted_not_blown_up():
    assert motion_residuals(CROSSES_ZERO)["rms_arcsec"] < 10


def test_a_track_crossing_zero_hours_does_not_appear_to_turn_around():
    angles = position_angles(CROSSES_ZERO)
    assert max(angles) - min(angles) < 20


def test_the_same_track_shifted_away_from_zero_measures_the_same():
    # The only difference is where it sits in RA, so nothing may depend on that.
    shifted = [
        detection(d["jd"], (d["ra"] + 180) % 360, d["dec"]) for d in CROSSES_ZERO
    ]
    near_zero = motion_residuals(CROSSES_ZERO)["rms_arcsec"]
    away = motion_residuals(shifted)["rms_arcsec"]
    assert abs(near_zero - away) < 0.01


def fixture_track():
    with open(FIXTURE) as f:
        return json.load(f)


def test_the_fixture_is_the_track_the_mpc_accepted():
    track = fixture_track()
    assert track["n_detections"] == len(track["detections"]) == 19
    # 13 object ids across 19 detections is the whole reason a track is needed.
    assert track["n_distinct_object_ids"] == 13


def test_the_fixture_jds_are_precise_enough_to_submit():
    # 1e-5 d is 0.86 s. A submission built from a rounded JD carries a timing
    # error nobody can see in the output, so the fixture has to be better.
    for row in fixture_track()["detections"]:
        decimals = len(str(row["jd"]).split(".")[-1])
        assert decimals >= 6, f"jd {row['jd']} is too coarse to timestamp"


def test_the_fixture_track_measures_as_one_smooth_arc():
    rows = fixture_track()["detections"]
    angles = position_angles(rows)
    # Monotonic to within the scatter of the same-night pairs, whose short
    # baselines make their angles noisy.
    assert angles[0] > angles[-1]
    assert motion_residuals(rows)["degree"] == 3
