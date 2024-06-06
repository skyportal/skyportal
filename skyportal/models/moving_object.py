__all__ = [
    'MovingObject',
    'MovingObjectAssociation',
]

import sqlalchemy as sa
from sqlalchemy.orm import deferred, relationship
from sqlalchemy.dialects.postgresql import ARRAY

from astropy.table import Table
import astropy.units as u
from astropy.coordinates import SkyCoord
from mocpy import MOC
import regions

from baselayer.app.models import Base


class MovingObject(Base):
    """Moving object"""

    __tablename__ = 'moving_objects'

    id = sa.Column(sa.String, primary_key=True, doc='Moving object name')

    mjd = deferred(
        sa.Column(ARRAY(sa.Float), nullable=True, doc='MJD of the moving object orbit.')
    )
    ra = deferred(
        sa.Column(
            ARRAY(sa.Float),
            nullable=True,
            doc="J2000 Right Ascension of the moving object orbit [deg].",
        )
    )
    dec = deferred(
        sa.Column(
            ARRAY(sa.Float),
            nullable=True,
            doc="J2000 Declination of the moving object orbit [deg].",
        )
    )
    ra_err = deferred(
        sa.Column(
            ARRAY(sa.Float),
            nullable=True,
            doc="Error on J2000 Right Ascension of the moving object orbit [deg].",
        )
    )
    dec_err = deferred(
        sa.Column(
            ARRAY(sa.Float),
            nullable=True,
            doc="Error on J2000 Declination of the moving object orbit [deg].",
        )
    )
    objs = relationship(
        'Obj',
        secondary='moving_object_associations',
        back_populates='moving_objects',
        passive_deletes=True,
        doc='Objects associated with this moving object.',
    )

    @property
    def table(self):
        """Get orbit dataset."""
        return Table(
            [self.mjd, self.ra, self.ra_err, self.dec, self.dec_err],
            names=['MJD', 'RA', 'RA_ERR', 'DEC', 'DEC_ERR'],
        )

    @property
    def localization(self):
        try:
            table = self.table
            row = table[-1]

            center = SkyCoord(row["RA"], row["DEC"], unit="deg", frame="icrs")

            if row["RA_ERR"] > row["DEC_ERR"]:
                ellipse = regions.EllipseSkyRegion(
                    center, row["DEC_ERR"] * u.deg, row["RA_ERR"] * u.deg, 0 * u.deg
                )
            else:
                ellipse = regions.EllipseSkyRegion(
                    center, row["RA_ERR"] * u.deg, row["DEC_ERR"] * u.deg, 90 * u.deg
                )
            moc = MOC.from_astropy_regions(ellipse, max_depth=10)

            return moc, center
        except Exception:
            return None, None

    @property
    def contour(self):
        moc, center = self.localization
        if moc is None or center is None:
            return None
        boundaries = moc.get_boundaries()

        # compute full contour
        geometry = []
        for coord in boundaries:
            tab = list(
                zip(
                    (*coord.ra.deg, coord.ra.deg[0]),
                    (*coord.dec.deg, coord.dec.deg[0]),
                )
            )
            geometry.append(tab)

        contour = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [center.ra.deg, center.dec.deg],
                    },
                    'properties': {'credible_level': 0},
                }
            ]
            + [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'MultiLineString',
                        'coordinates': geometry,
                    },
                },
            ],
        }

        return contour


class MovingObjectAssociation(Base):
    """Association between moving objects and objects."""

    __tablename__ = 'moving_object_associations'

    moving_object_id = sa.Column(
        sa.String,
        sa.ForeignKey('moving_objects.id', ondelete='CASCADE'),
        primary_key=True,
        doc='Moving object name',
    )
    obj_id = sa.Column(
        sa.String,
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        primary_key=True,
        doc='Object ID',
    )

    moving_object = relationship(
        'MovingObject',
        foreign_keys=[moving_object_id],
        doc='Moving object associated with this object.',
        overlaps="moving_objects,objs",
    )
    obj = relationship(
        'Obj',
        foreign_keys=[obj_id],
        doc='Object associated with this moving object.',
        overlaps="moving_objects,objs",
    )


# AllocationUser = join_model('allocation_users', Allocation, User)
