from skyportal.utils.offset import get_astrometry_backup_from_ztf


def test_get_astrometry_backup_from_ztf():
    # This is a source in the ZTF Catalog
    source_ra, source_dec = 122.8065388, 43.9410025
    rez = get_astrometry_backup_from_ztf(source_ra, source_dec, max_offset_arcsec=60)
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
