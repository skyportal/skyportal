import numpy as np

from skyportal.utils.catalog import tesselation_spiral


def _expected_n(fov, scale=0.80):
    area_of_sphere = 4 * np.pi * (180 / np.pi) ** 2
    return int(np.ceil(area_of_sphere / (np.pi * fov * fov * scale)))


def test_tile_count_matches_formula():
    for fov in (2.0, 5.0, 10.0):
        ra, dec = tesselation_spiral(fov)
        assert len(ra) == len(dec) == _expected_n(fov)


def test_centers_within_sky_ranges():
    ra, dec = tesselation_spiral(5.0)
    assert len(ra) > 0
    assert np.all((ra >= 0) & (ra <= 360))
    assert np.all((dec >= -90) & (dec <= 90))


def test_larger_fov_gives_fewer_tiles():
    assert len(tesselation_spiral(10.0)[0]) < len(tesselation_spiral(2.0)[0])


def test_deterministic():
    ra1, dec1 = tesselation_spiral(5.0)
    ra2, dec2 = tesselation_spiral(5.0)
    np.testing.assert_array_equal(ra1, ra2)
    np.testing.assert_array_equal(dec1, dec2)


def test_scale_affects_tile_count():
    # smaller scale -> smaller effective area per circle -> more tiles needed
    assert len(tesselation_spiral(5.0, scale=0.5)[0]) > len(
        tesselation_spiral(5.0, scale=0.95)[0]
    )
