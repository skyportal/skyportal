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


def test_every_camera_centre_is_in_its_sector(tess_fields):
    # All four rather than one. A position bound with the wrong healpix encoding
    # resolves somewhere else entirely, and a single camera centre can still land
    # on another camera of the same sector by chance.
    for camera, ra, dec, _ in camera_pointings(SECTOR):
        sectors = sectors_containing(DBSession(), tess_fields.id, _healpix_at(ra, dec))
        assert sectors == [SECTOR], f"camera {camera}"


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


def _select(session, now, limit=10):
    """Object ids the service would pick up for annotation."""
    import sys

    sys.path.insert(0, "services/tess_sector")
    from tess_sector import needs_annotation

    return {obj.id for obj in session.scalars(needs_annotation(now, limit)).all()}


def _annotate_with(session, obj, user, group, sectors, in_current_sector):
    from skyportal.models import Annotation

    session.add(
        Annotation(
            obj_id=obj.id,
            origin=ANNOTATION_ORIGIN,
            data={"sectors": sectors, "in_current_sector": in_current_sector},
            author_id=user.id,
            groups=[group],
        )
    )
    session.commit()


def test_an_unannotated_candidate_is_selected(
    public_candidate, public_group, super_admin_user
):
    public_candidate.healpix = _healpix_at(10.0, -20.0)
    DBSession().commit()
    assert public_candidate.id in _select(DBSession(), SECTOR)


def test_a_candidate_with_no_position_is_not_selected(
    public_candidate, public_group, super_admin_user
):
    public_candidate.healpix = None
    DBSession().commit()
    assert public_candidate.id not in _select(DBSession(), SECTOR)


def test_an_annotation_that_still_holds_is_left_alone(
    public_candidate, public_group, super_admin_user
):
    public_candidate.healpix = _healpix_at(10.0, -20.0)
    DBSession().commit()
    # in_current_sector agrees with SECTOR being in `sectors`.
    _annotate_with(
        DBSession(), public_candidate, super_admin_user, public_group, [SECTOR], True
    )
    assert public_candidate.id not in _select(DBSession(), SECTOR)


def test_an_annotation_the_sector_has_moved_past_is_reselected(
    public_candidate, public_group, super_admin_user
):
    public_candidate.healpix = _healpix_at(10.0, -20.0)
    DBSession().commit()
    # Stored true, but the object is not in the sector observing now: stale.
    _annotate_with(
        DBSession(), public_candidate, super_admin_user, public_group, [SECTOR], True
    )
    assert public_candidate.id in _select(DBSession(), SECTOR + 1)


def test_between_sectors_a_stored_true_is_stale(
    public_candidate, public_group, super_admin_user
):
    public_candidate.healpix = _healpix_at(10.0, -20.0)
    DBSession().commit()
    _annotate_with(
        DBSession(), public_candidate, super_admin_user, public_group, [SECTOR], True
    )
    assert public_candidate.id in _select(DBSession(), None)


def test_between_sectors_a_stored_false_still_holds(
    public_candidate, public_group, super_admin_user
):
    public_candidate.healpix = _healpix_at(10.0, -20.0)
    DBSession().commit()
    _annotate_with(
        DBSession(), public_candidate, super_admin_user, public_group, [SECTOR], False
    )
    assert public_candidate.id not in _select(DBSession(), None)
