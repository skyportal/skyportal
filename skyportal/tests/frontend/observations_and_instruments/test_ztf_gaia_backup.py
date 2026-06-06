import pytest

from skyportal.utils.offset import get_astrometry_backup_from_ztf


def test_get_astrometry_backup_from_ztf():
    # A real, high-SNR source in the ZTF reference PSF catalog. (The previous
    # coordinate had drifted just outside the reference image footprint that
    # get_ztfref_url now selects, so the nearest catalog source was ~150" away
    # and the query came back empty -- a stale-coordinate problem, not a code or
    # service problem.)
    source_ra, source_dec = 122.8672801, 44.1140034
    rez = get_astrometry_backup_from_ztf(source_ra, source_dec, max_offset_arcsec=60)
    # get_astrometry_backup_from_ztf returns None when the external ZTF reference
    # catalog service is unreachable; skip rather than fail the suite in that case.
    if rez is None:
        pytest.skip("ZTF reference catalog service unavailable")
    rez.sort("dist")
    # We should find a number of sources, with the first one being near
    # the known source
    assert rez["dist"][0] < 30.0 / 3600.0


def test_get_astrometry_outside_footprint():
    # This is a source in the ZTF Catalog
    source_ra, source_dec = 123, -75
    rez = get_astrometry_backup_from_ztf(source_ra, source_dec, max_offset_arcsec=60)
    # We should find no sources here since this is in the Southern Hemisphere
    # expect to get None
    assert len(rez) == 0
