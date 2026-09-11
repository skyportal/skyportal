"""RAVEN's sky-map overlap integral.

``I = 4 pi * integral(p1 p2) dOmega`` has known values for simple maps, so it is
checked against those rather than against itself: 1 for two uniform maps, 0 for
disjoint ones, and 1/f for two copies of a map covering a fraction f of the sky.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from skyportal.utils.crossmatch import (
    skymap_consistency,
    skymap_overlap_integral,
)

# level 0 is nside 1: 12 pixels, uniq = 4 + ipix
LEVEL0 = [4 + i for i in range(12)]
# the four level-1 children of level-0 pixel 0
CHILDREN_OF_0 = [16 + i for i in range(4)]
PIXEL_DENSITY = 12 / (4 * np.pi)  # a map concentrated in one level-0 pixel


def _localization(uniq, probdensity):
    return SimpleNamespace(
        uniq=np.array(uniq, dtype=np.int64),
        probdensity=np.array(probdensity, dtype=float),
    )


def test_uniform_maps_are_uncorrelated():
    uniform = _localization(LEVEL0, [1 / (4 * np.pi)] * 12)
    assert skymap_overlap_integral(uniform, uniform) == pytest.approx(1.0)


def test_disjoint_maps_do_not_overlap():
    here = _localization([4], [PIXEL_DENSITY])
    elsewhere = _localization([9], [PIXEL_DENSITY])
    assert skymap_overlap_integral(here, elsewhere) == 0.0


def test_identical_maps_overlap_by_their_concentration():
    """A map confined to 1/12 of the sky overlaps itself with I = 12."""
    pixel = _localization([4], [PIXEL_DENSITY])
    assert skymap_overlap_integral(pixel, pixel) == pytest.approx(12.0)


def test_resolutions_need_not_match():
    """The reason for range arithmetic: one map's cell is another's four.

    A level-0 pixel against the four level-1 children covering exactly it must
    give the same answer as against itself -- no rasterization to a common grid.
    """
    coarse = _localization([4], [PIXEL_DENSITY])
    fine = _localization(CHILDREN_OF_0, [PIXEL_DENSITY] * 4)
    assert skymap_overlap_integral(coarse, fine) == pytest.approx(12.0)


def test_partial_overlap_counts_only_the_shared_area():
    """Half the pixel at twice the density carries the same probability."""
    coarse = _localization([4], [PIXEL_DENSITY])
    half = _localization(CHILDREN_OF_0[:2], [2 * PIXEL_DENSITY] * 2)
    assert skymap_overlap_integral(coarse, half) == pytest.approx(12.0)


def test_empty_map_overlaps_nothing():
    pixel = _localization([4], [PIXEL_DENSITY])
    empty = _localization([], [])
    assert skymap_overlap_integral(pixel, empty) == 0.0
    assert skymap_overlap_integral(empty, pixel) == 0.0


def test_consistency_is_one_for_identical_maps_of_any_size():
    """The point of normalising: the raw overlap cannot be compared across pairs.

    Two identical maps score 1 whether they cover the whole sky or a twelfth of
    it, while the overlap integral for the same two cases is 1 and 12.
    """
    uniform = _localization(LEVEL0, [1 / (4 * np.pi)] * 12)
    pixel = _localization([4], [PIXEL_DENSITY])

    assert skymap_consistency(uniform, uniform) == pytest.approx(1.0)
    assert skymap_consistency(pixel, pixel) == pytest.approx(1.0)
    # ... from overlaps that differ by more than an order of magnitude
    assert skymap_overlap_integral(uniform, uniform) == pytest.approx(1.0)
    assert skymap_overlap_integral(pixel, pixel) == pytest.approx(12.0)


def test_consistency_of_disjoint_maps_is_zero():
    here = _localization([4], [PIXEL_DENSITY])
    elsewhere = _localization([9], [PIXEL_DENSITY])
    assert skymap_consistency(here, elsewhere) == 0.0


def test_consistency_of_partial_agreement():
    """Half the pixel at twice the density: the correlation is 1/sqrt(2)."""
    coarse = _localization([4], [PIXEL_DENSITY])
    half = _localization(CHILDREN_OF_0[:2], [2 * PIXEL_DENSITY] * 2)
    assert skymap_consistency(coarse, half) == pytest.approx(1 / np.sqrt(2), abs=1e-6)


def test_consistency_never_exceeds_one():
    """Cauchy-Schwarz bounds it, and the code clamps the floating-point edge."""
    coarse = _localization([4], [PIXEL_DENSITY])
    fine = _localization(CHILDREN_OF_0, [PIXEL_DENSITY] * 4)
    assert skymap_consistency(coarse, fine) <= 1.0
    assert skymap_consistency(coarse, fine) == pytest.approx(1.0)
