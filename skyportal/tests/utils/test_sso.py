import math

import pytest

from skyportal.utils.sso import (
    fit_band_colors,
    hg12_phase_function,
    outburst_report,
    reduce_to_unit_geometry,
)

# (phase angle deg, reduced mag) from sbpy HG12_Pen16.evaluate(a, 0, 0.5).
SBPY_FIXTURES = [
    (0.0, 0.0),
    (2.0, 0.2605584839),
    (10.0, 0.6519214327),
    (30.0, 1.2737335665),
    (60.0, 2.1231978882),
    (90.0, 3.1380204198),
]


@pytest.mark.parametrize(("phase", "expected"), SBPY_FIXTURES)
def test_phase_function_matches_sbpy(phase, expected):
    assert hg12_phase_function(phase) == pytest.approx(expected, abs=1e-6)


def _synthetic(h=15.2, colors=None, n_nights=20):
    """A body of fixed absolute magnitude seen over a range of geometry."""
    colors = colors or {"r": 0.0, "g": 0.5}
    points, time = [], 60000.0
    for k in range(n_nights):
        time += 3.0
        # Geometry has to stay physical over the whole run: delta > 0.
        rh = 2.8 - 0.025 * k
        delta, phase = rh - 0.9, 4.0 + 0.4 * k
        for band, color in colors.items():
            mag = h + color + 5 * math.log10(rh * delta) + hg12_phase_function(phase)
            points.append(
                {
                    "time": time,
                    "mag": mag,
                    "magerr": 0.02,
                    "band": band,
                    "rh": rh,
                    "delta": delta,
                    "phase": phase,
                }
            )
    return points


def test_reduction_flattens_a_fixed_brightness_body():
    # Fixed brightness at wildly varying geometry must reduce flat.
    points = _synthetic()
    reduced = reduce_to_unit_geometry(
        [p["mag"] for p in points if p["band"] == "r"],
        [p["rh"] for p in points if p["band"] == "r"],
        [p["delta"] for p in points if p["band"] == "r"],
        [p["phase"] for p in points if p["band"] == "r"],
    )
    assert max(reduced) - min(reduced) < 1e-9
    assert reduced[0] == pytest.approx(15.2)


def test_colors_recover_the_input_offsets():
    fit = fit_band_colors(_synthetic(colors={"r": 0.0, "g": 0.51, "i": -0.12}))
    assert fit["reference"] == "r"
    assert fit["colors"]["g"]["offset"] == pytest.approx(0.51, abs=1e-9)
    assert fit["colors"]["i"]["offset"] == pytest.approx(-0.12, abs=1e-9)
    assert fit["colors"]["r"]["offset"] == 0.0


def test_rejected_points_are_never_fitted():
    points = _synthetic()
    clean = fit_band_colors(points)["colors"]["g"]["offset"]
    points.append(
        {**points[-1], "mag": points[-1]["mag"] - 3.0, "band": "g", "rejected": True}
    )
    assert fit_band_colors(points)["colors"]["g"]["offset"] == pytest.approx(clean)


def test_quiet_object_shows_no_outburst():
    report = outburst_report(_synthetic(n_nights=40), window=20)
    assert abs(report["median_o"]) < 1.0


def test_brightening_in_the_trailing_window_is_flagged():
    points = _synthetic(n_nights=40)
    # The statistic tests the most recent point, so brighten that one.
    points[-1] = {**points[-1], "mag": points[-1]["mag"] - 1.0}
    assert outburst_report(points, window=20)["median_o"] > 3


def test_reduction_needs_positive_geometry():
    assert math.isnan(reduce_to_unit_geometry([18.0], [0.0], [1.0], [5.0])[0])
