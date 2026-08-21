"""Unit tests for the asteroid outburst statistic and its numpy HG12 phase
function. The phase-function fixtures were generated from sbpy's HG12_Pen16
(G12=0.5); the statistic assertions are M. Kelley's reference tests.
"""

import numpy as np
import pytest

from skyportal.utils.outburst import (
    DEFAULT_DELTA_SLOPE,
    DEFAULT_RH_SLOPE,
    hg12_phase_function,
    outburst_report,
    outburst_statistic,
)

# (phase angle deg, reduced magnitude) from sbpy HG12_Pen16.evaluate(a, 0, 0.5)
_HG12_FIXTURES = [
    (0.0, 0.0000000008),
    (0.3, 0.0633709047),
    (1.0, 0.1740955589),
    (2.0, 0.2605581834),
    (4.0, 0.3962880010),
    (7.5, 0.5582150592),
    (10.0, 0.6519205937),
    (20.0, 0.9873850487),
    (30.0, 1.2737341391),
    (45.0, 1.6870530694),
    (60.0, 2.1231979283),
    (90.0, 3.1380201178),
    (120.0, 4.5573412276),
    (150.0, 7.0046078063),
]


@pytest.mark.parametrize("alpha,expected", _HG12_FIXTURES)
def test_hg12_matches_sbpy(alpha, expected):
    assert np.isclose(hg12_phase_function(alpha), expected, atol=1e-6)


def test_hg12_vectorized():
    alphas = np.array([a for a, _ in _HG12_FIXTURES])
    expected = np.array([e for _, e in _HG12_FIXTURES])
    assert np.allclose(hg12_phase_function(alphas), expected, atol=1e-6)


# ---- M. Kelley's reference tests: the statistic corrects each effect ----

_EXPECTED = 1 / np.sqrt(2 * 0.1**2)  # a 1-mag jump at unc=0.1 on both points


def _to_mag(x):
    return -2.5 * np.log10(x)


def test_statistic_positive_for_brightening():
    o, _, _ = outburst_statistic(
        [1, 1], [1, 1], [0, 0], [0, -1], [0.1, 0.1], ["r", "r"]
    )
    assert np.isclose(o, _EXPECTED)


def test_statistic_corrects_phase():
    o, _, _ = outburst_statistic(
        [1, 1], [1, 1], [30, 0], [hg12_phase_function(30), -1], [0.1, 0.1], ["r", "r"]
    )
    assert np.isclose(o, _EXPECTED)


def test_statistic_corrects_delta():
    o, _, _ = outburst_statistic(
        [1, 1],
        [2, 1],
        [0, 0],
        [_to_mag(2**DEFAULT_DELTA_SLOPE), -1],
        [0.1, 0.1],
        ["r", "r"],
    )
    assert np.isclose(o, _EXPECTED)


def test_statistic_corrects_rh():
    o, _, _ = outburst_statistic(
        [4, 1],
        [1, 1],
        [0, 0],
        [_to_mag(4**DEFAULT_RH_SLOPE), -1],
        [0.1, 0.1],
        ["r", "r"],
    )
    assert np.isclose(o, _EXPECTED)


def test_statistic_corrects_color():
    o, _, _ = outburst_statistic(
        [1, 1, 1],
        [1, 1, 1],
        [0, 0, 0],
        [0, 0.5, -1],
        [0.1, 0.1, 0.1],
        ["r", "g", "r"],
    )
    assert np.allclose(o, [_EXPECTED, _EXPECTED])


# ---- outburst_report: windowing + panel assembly ----

_N = 14
_TIME = np.arange(_N, dtype=float)  # dt spans -13..0, all within a 14-day window
_BANDS = np.array(["g", "r"] * (_N // 2))
_M_FLAT = np.where(_BANDS == "g", 16.6, 17.0)  # constant, g-r = -0.4
_UNC = np.full(_N, 0.1)
_ONE = np.ones(_N)
_ZERO = np.zeros(_N)


def test_report_flat_is_no_outburst():
    r = outburst_report(_TIME, _M_FLAT, _UNC, _BANDS, _ONE, _ONE, _ZERO, window=14)
    assert r["n_points"] == _N
    assert np.isclose(r["median_o"], 0.0, atol=1e-9)
    # colour removal collapses the two bands onto one relation
    assert np.std(r["H_color"]) < 1e-9
    assert np.isclose(r["test_value"], 17.0)


def test_report_detects_brightening():
    m = _M_FLAT.copy()
    m[-1] = 17.0 - 0.5  # most recent r point 0.5 mag brighter
    r = outburst_report(_TIME, m, _UNC, _BANDS, _ONE, _ONE, _ZERO, window=14)
    assert np.isclose(r["median_o"], 0.5 / (0.1 * np.sqrt(2)))


def test_report_orders_and_windows():
    # shuffle, and add a point well outside the window
    rng = np.random.default_rng(0)
    idx = rng.permutation(_N)
    time = np.concatenate([_TIME[idx], [-30.0]])
    m = np.concatenate([_M_FLAT[idx], [10.0]])  # bright, but out of window
    unc = np.concatenate([_UNC, [0.1]])
    bands = np.concatenate([_BANDS[idx], ["r"]])
    one = np.ones(_N + 1)
    zero = np.zeros(_N + 1)
    r = outburst_report(time, m, unc, bands, one, one, zero, window=14)
    assert r["n_points"] == _N  # the out-of-window point is dropped
    assert np.isclose(r["dt"][-1], 0.0)  # test point is the most recent
    assert np.all(np.diff(r["dt"]) >= 0)  # ordered by time
    assert np.isclose(r["median_o"], 0.0, atol=1e-9)
