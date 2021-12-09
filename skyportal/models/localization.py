__all__ = ['Localization']

import sqlalchemy as sa
from sqlalchemy.orm import relationship, deferred
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

from astropy.table import Table
import numpy as np
import ligo.skymap.bayestar as ligo_bayestar
import healpy

from baselayer.app.models import Base, AccessibleIfUserMatches


class Localization(Base):
    """Localization information, including the localization ID, event ID, right
    ascension, declination, error radius (if applicable), and the healpix
    map."""

    update = delete = AccessibleIfUserMatches('sent_by')

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this Localization.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="localizations",
        doc="The user that saved this Localization",
    )

    nside = 512
    # HEALPix resolution used for flat (non-multiresolution) operations.

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc='UTC event timestamp',
    )

    localization_name = sa.Column(sa.String, doc='Localization name', index=True)

    uniq = deferred(
        sa.Column(
            sa.ARRAY(sa.BigInteger),
            nullable=False,
            doc='Multiresolution HEALPix UNIQ pixel index array',
        )
    )

    probdensity = deferred(
        sa.Column(
            sa.ARRAY(sa.Float),
            nullable=False,
            doc='Multiresolution HEALPix probability density array',
        )
    )

    distmu = deferred(
        sa.Column(sa.ARRAY(sa.Float), doc='Multiresolution HEALPix distance mu array')
    )

    distsigma = deferred(
        sa.Column(
            sa.ARRAY(sa.Float), doc='Multiresolution HEALPix distance sigma array'
        )
    )

    distnorm = deferred(
        sa.Column(
            sa.ARRAY(sa.Float),
            doc='Multiresolution HEALPix distance normalization array',
        )
    )

    contour = deferred(sa.Column(JSONB, doc='GeoJSON contours'))

    @hybrid_property
    def is_3d(self):
        return (
            self.distmu is not None
            and self.distsigma is not None
            and self.distnorm is not None
        )

    @is_3d.expression
    def is_3d(cls):
        return sa.and_(
            cls.distmu.isnot(None),
            cls.distsigma.isnot(None),
            cls.distnorm.isnot(None),
        )

    @property
    def table_2d(self):
        """Get multiresolution HEALPix dataset, probability density only."""
        return Table(
            [np.asarray(self.uniq, dtype=np.int64), self.probdensity],
            names=['UNIQ', 'PROBDENSITY'],
        )

    @property
    def table(self):
        """Get multiresolution HEALPix dataset, probability density and
        distance."""
        if self.is_3d:
            return Table(
                [
                    np.asarray(self.uniq, dtype=np.int64),
                    self.probdensity,
                    self.distmu,
                    self.distsigma,
                    self.distnorm,
                ],
                names=['UNIQ', 'PROBDENSITY', 'DISTMU', 'DISTSIGMA', 'DISTNORM'],
            )
        else:
            return self.table_2d

    @property
    def flat_2d(self):
        """Get flat resolution HEALPix dataset, probability density only."""
        order = healpy.nside2order(Localization.nside)
        result = ligo_bayestar.rasterize(self.table_2d, order)['PROB']
        return healpy.reorder(result, 'NESTED', 'RING')

    @property
    def flat(self):
        """Get flat resolution HEALPix dataset, probability density and
        distance."""
        if self.is_3d:
            order = healpy.nside2order(Localization.nside)
            t = ligo_bayestar.rasterize(self.table, order)
            result = t['PROB'], t['DISTMU'], t['DISTSIGMA'], t['DISTNORM']
            return healpy.reorder(result, 'NESTED', 'RING')
        else:
            return (self.flat_2d,)
