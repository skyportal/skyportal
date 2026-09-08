import astropy.units as u
import pytest
from astropy.coordinates import SkyCoord
from astropy.time import Time

from skyportal.utils.tess import (
    all_sectors,
    annotation_data,
    camera_pointings,
    current_sector,
    field_data,
    field_id_for,
    missing_field_data,
    pointings,
    sector_of,
    sector_window,
)


def test_field_id_round_trips_the_sector():
    assert sector_of(field_id_for(97, 3)) == 97
    assert field_id_for(97, 1) != field_id_for(97, 2)
    with pytest.raises(ValueError):
        field_id_for(97, 5)


def test_every_sector_has_four_cameras_24_degrees_apart():
    """The cameras sit on one great circle, adjacent centres 24 deg apart."""
    for sector in (1, 40, 97):
        cams = camera_pointings(sector)
        assert len(cams) == 4
        centres = [SkyCoord(ra * u.deg, dec * u.deg) for _, ra, dec, _ in cams]
        for a, b in zip(centres, centres[1:]):
            assert a.separation(b).deg == pytest.approx(24.0, abs=0.01)


def test_camera_one_sits_36_degrees_from_the_boresight():
    row = next(p for p in pointings()["pointings"] if p["sector"] == 1)
    boresight = SkyCoord(row["ra"] * u.deg, row["dec"] * u.deg)
    _, ra, dec, _ = camera_pointings(1)[0]
    sep = SkyCoord(ra * u.deg, dec * u.deg).separation(boresight).deg
    assert sep == pytest.approx(36.0, abs=0.01)


def test_camera_centres_match_the_published_pointing():
    """Sector 1's camera centres, from the TESS Science Office."""
    expected = [
        (324.567, -33.173),
        (338.577, -55.079),
        (19.493, -71.978),
        (90.004, -66.565),
    ]
    for (_, ra, dec, _), (want_ra, want_dec) in zip(camera_pointings(1), expected):
        assert SkyCoord(ra * u.deg, dec * u.deg).separation(
            SkyCoord(want_ra * u.deg, want_dec * u.deg)
        ).deg == pytest.approx(0.0, abs=0.001)


def test_current_sector_is_none_between_sectors():
    """Sectors leave a downlink gap, so some instants belong to no sector."""
    assert current_sector(Time("2000-01-01")) is None


def test_current_sector_finds_the_sector_observing_then():
    row = pointings()["pointings"][10]
    mid = Time(row["midtime_jd"], format="jd")
    assert current_sector(mid) == row["sector"]
    start, end = sector_window(row["sector"])
    assert start < mid < end


def test_field_data_is_shaped_for_the_instrument_post():
    data = field_data([1, 2])
    assert set(data) == {"ID", "RA", "Dec", "rotation"}
    assert len(data["ID"]) == 8
    assert len(set(data["ID"])) == 8
    assert all(0 <= r < 90 for r in data["rotation"])
    assert all(0 <= ra <= 360 for ra in data["RA"])
    assert all(-90 <= dec <= 90 for dec in data["Dec"])


def test_loading_is_incremental():
    """Publishing a new sector means adding a row; the next run fills it in."""
    sectors = all_sectors()
    loaded = [
        field_id_for(sector, camera)
        for sector in sectors[:-1]
        for camera in range(1, 5)
    ]
    data = missing_field_data(loaded)
    assert data is not None
    assert sorted(data["ID"]) == sorted(
        field_id_for(sectors[-1], camera) for camera in range(1, 5)
    )

    # Nothing to do once every sector is present.
    every = loaded + [field_id_for(sectors[-1], c) for c in range(1, 5)]
    assert missing_field_data(every) is None


def test_a_half_loaded_sector_is_completed():
    """A sector interrupted mid-load is finished rather than left short."""
    sectors = all_sectors()
    loaded = [
        field_id_for(sector, camera) for sector in sectors for camera in range(1, 5)
    ]
    loaded.remove(field_id_for(sectors[3], 2))
    data = missing_field_data(loaded)
    assert sorted(data["ID"]) == sorted(
        field_id_for(sectors[3], camera) for camera in range(1, 5)
    )


def test_annotation_separates_ever_observed_from_currently_observing():
    row = pointings()["pointings"][5]
    mid = Time(row["midtime_jd"], format="jd")

    covered = annotation_data([row["sector"], row["sector"] + 40], when=mid)
    assert covered["observed"] is True
    assert covered["in_current_sector"] is True
    assert covered["current_sector"] == row["sector"]

    # Observed in the past, but not by the sector running now.
    elsewhere = annotation_data([row["sector"] + 40], when=mid)
    assert elsewhere["observed"] is True
    assert elsewhere["in_current_sector"] is False
    assert elsewhere["current_sector"] is None

    never = annotation_data([], when=mid)
    assert never["observed"] is False and never["sectors"] == []
