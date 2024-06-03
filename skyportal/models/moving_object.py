__all__ = [
    'MovingObject',
]

import sqlalchemy as sa
from sqlalchemy.orm import deferred
from sqlalchemy.dialects.postgresql import ARRAY

from astropy.table import Table

from baselayer.app.models import Base


class MovingObject(Base):
    """Moving object"""

    __tablename__ = 'moving_object'

    name = sa.Column(
        sa.String, unique=True, nullable=False, doc='Moving object name', index=True
    )

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
    obj_ids = sa.Column(
        ARRAY(sa.String), doc="Objects associated with the moving object."
    )

    @property
    def table(self):
        """Get orbit dataset."""
        return Table(
            [self.mjd, self.ra, self.ra_err, self.dec, self.dec_err],
            names=['MJD', 'RA', 'RA_ERR', 'DEC', 'DEC_ERR'],
        )
