"""TESS coverage against real field tiles."""

import astropy.units as u
import pytest
from astropy.coordinates import SkyCoord

from skyportal.handlers.api.instrument import add_tiles
from skyportal.models import DBSession
from skyportal.utils.tess import (
    ANNOTATION_ORIGIN,
    camera_pointings,
    camera_region,
    field_data,
)
from skyportal.utils.tess_ingest import annotate_object, sectors_containing

SECTOR = 50


@pytest.fixture()
def tess_fields(lris):
    """One sector's four camera footprints, tiled onto a spare instrument."""
    add_tiles(
        lris.id,
        lris.name,
        camera_region(),
        field_data([SECTOR]),
        session=DBSession(),
    )
    DBSession().commit()
    return lris


def _healpix_at(ra, dec):
    from healpix_alchemy.constants import HPX

    return HPX.skycoord_to_healpix(SkyCoord(ra * u.deg, dec * u.deg))


def test_a_camera_centre_is_in_its_sector(tess_fields):
    _, ra, dec, _ = camera_pointings(SECTOR)[0]
    sectors = sectors_containing(DBSession(), tess_fields.id, _healpix_at(ra, dec))
    assert sectors == [SECTOR]


def test_a_position_well_off_the_cameras_is_in_no_sector(tess_fields):
    """The anti-pointing: 180 degrees from the boresight is never on silicon."""
    _, ra, dec, _ = camera_pointings(SECTOR)[0]
    opposite = SkyCoord(ra * u.deg, dec * u.deg).directional_offset_by(
        0 * u.deg, 180 * u.deg
    )
    sectors = sectors_containing(
        DBSession(),
        tess_fields.id,
        _healpix_at(opposite.ra.deg, opposite.dec.deg),
    )
    assert sectors == []


def test_annotation_records_the_coverage(
    tess_fields, public_source, public_group, super_admin_user
):
    _, ra, dec, _ = camera_pointings(SECTOR)[0]
    public_source.ra = ra
    public_source.dec = dec
    public_source.healpix = _healpix_at(ra, dec)
    DBSession().commit()

    data = annotate_object(
        DBSession(),
        public_source,
        tess_fields.id,
        super_admin_user.id,
        [public_group.id],
    )
    DBSession().commit()

    assert data["sectors"] == [SECTOR]
    assert data["observed"] is True

    from skyportal.models import Annotation

    annotation = DBSession().scalar(
        Annotation.select(super_admin_user).where(
            Annotation.obj_id == public_source.id,
            Annotation.origin == ANNOTATION_ORIGIN,
        )
    )
    assert annotation.data["sectors"] == [SECTOR]


def test_an_object_without_a_position_is_skipped(
    tess_fields, public_source, public_group, super_admin_user
):
    public_source.healpix = None
    DBSession().commit()
    assert (
        annotate_object(
            DBSession(),
            public_source,
            tess_fields.id,
            super_admin_user.id,
            [public_group.id],
        )
        is None
    )
