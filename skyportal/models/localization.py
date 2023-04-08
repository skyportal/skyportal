__all__ = [
    'Localization',
    'LocalizationTag',
    'LocalizationProperty',
    'LocalizationTile',
]

import datetime

import arrow
import dustmaps.sfd
import healpix_alchemy
import healpy
import ligo.skymap.bayestar as ligo_bayestar
import ligo.skymap.postprocess
import numpy as np
import sqlalchemy as sa
from astropy.table import Table
from dateutil.relativedelta import relativedelta
from dustmaps.config import config
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import deferred, relationship
from sqlalchemy.sql.ddl import DDL

from baselayer.app.env import load_env
from baselayer.app.models import AccessibleIfUserMatches, Base

_, cfg = load_env()
config['data_dir'] = cfg['misc.dustmap_folder']


class PartitionByMeta(DeclarativeMeta):
    def __new__(cls, clsname, bases, attrs, *, partition_by, partition_type):
        @classmethod
        def get_partition_name(cls_, suffix):
            return f'{cls_.__tablename__}_{suffix}'

        @classmethod
        def create_partition(
            cls_, suffix, partition_stmt, subpartition_by=None, subpartition_type=None
        ):
            if suffix not in cls_.partitions:

                partition = PartitionByMeta(
                    f'{clsname}{suffix}',
                    bases,
                    {'__tablename__': cls_.get_partition_name(suffix)},
                    partition_type=subpartition_type,
                    partition_by=subpartition_by,
                )

                partition.__table__.add_is_dependent_on(cls_.__table__)
                event.listen(
                    partition.__table__,
                    'after_create',
                    DDL(
                        f"""
                        ALTER TABLE {cls_.__tablename__}
                        ATTACH PARTITION {partition.__tablename__}
                        {partition_stmt};
                        """
                    ),
                )

                cls_.partitions[suffix] = partition

            return cls_.partitions[suffix]

        if partition_by is not None:
            attrs.update(
                {
                    '__table_args__': attrs.get('__table_args__', ())
                    + (
                        dict(
                            postgresql_partition_by=f'{partition_type.upper()}({partition_by})'
                        ),
                    ),
                    'partitions': {},
                    'partitioned_by': partition_by,
                    'get_partition_name': get_partition_name,
                    'create_partition': create_partition,
                }
            )

        return super().__new__(cls, clsname, bases, attrs)


class Localization(Base):
    """Localization information, including the localization ID, event ID, right
    ascension, declination, error radius (if applicable), and the healpix
    map. The healpix map is a multi-order healpix skymap, and this
    representation of the skymap has many tiles (in the
    LocalizationTile table). Healpix decomposes the sky into a set of equal
    area tiles each with a unique index, convenient for decomposing
    the sphere into subdivisions."""

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

    observationplan_requests = relationship(
        'ObservationPlanRequest',
        back_populates='localization',
        cascade='delete',
        passive_deletes=True,
        doc="Observation plan requests of the localization.",
    )

    survey_efficiency_analyses = relationship(
        'SurveyEfficiencyForObservations',
        back_populates='localization',
        cascade='delete',
        passive_deletes=True,
        doc="Survey efficiency analyses of the event.",
    )

    properties = relationship(
        'LocalizationProperty',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="LocalizationProperty.created_at",
        doc="Properties associated with this Localization.",
    )

    tags = relationship(
        'LocalizationTag',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="LocalizationTag.created_at",
        doc="Tags associated with this Localization.",
    )

    notice_id = sa.Column(
        sa.ForeignKey('gcnnotices.id', ondelete='CASCADE'),
        nullable=True,
        doc="The ID of the Notice that this Localization is associated with, if any.",
    )

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

    @property
    def center(self):
        """Get information about the center of the localization."""

        prob = self.flat_2d
        coord = ligo.skymap.postprocess.posterior_max(prob)

        center_info = {}
        center_info["ra"] = coord.ra.deg
        center_info["dec"] = coord.dec.deg
        center_info["gal_lat"] = coord.galactic.b.deg
        center_info["gal_lon"] = coord.galactic.l.deg

        try:
            ebv = float(dustmaps.sfd.SFDQuery()(coord))
        except Exception:
            ebv = None
        center_info["ebv"] = ebv

        return center_info


class LocalizationTileMixin:
    """This is a single tile within a skymap (as in the Localization table).
    Each tile has an associated healpix id and probability density."""

    localization_id = sa.Column(
        sa.ForeignKey('localizations.id', ondelete="CASCADE"),
        primary_key=True,
        index=True,
        doc='localization ID',
    )

    probdensity = sa.Column(
        sa.Float,
        nullable=False,
        index=True,
        doc="Probability density for the tile",
    )

    dateobs = sa.Column(
        sa.DateTime,
        nullable=False,
        primary_key=True,
        doc="Date of observation for the Localization to which this tile belongs",
    )

    healpix = sa.Column(healpix_alchemy.Tile, primary_key=True, index=True)


class LocalizationTile(
    LocalizationTileMixin,
    Base,
    metaclass=PartitionByMeta,
    partition_by='dateobs',
    partition_type='RANGE',
):
    __tablename__ = 'localizationtiles'
    __table_args__ = (
        sa.Index(
            'localizationtile_id_healpix_dateobs_index',
            'id',
            'healpix',
            'dateobs',
            unique=True,
        ),
    )


LocalizationTile.create_partition("def", partition_stmt="DEFAULT")

# create partitions from 2017-01-01 to 2026-01-01, this could be speficied in the config
# TODO: but we need alembic to not keep track if every partition, just the original partitioned table
for year in range(2017, 2026):
    for month in range(1, 13):
        date = datetime.date(year, month, 1)
        LocalizationTile.create_partition(
            date.strftime("%Y_%m"),
            partition_stmt="FOR VALUES FROM ('{}') TO ('{}')".format(
                date.strftime("%Y-%m-%d"),
                (date + relativedelta(months=1)).strftime("%Y-%m-%d"),
            ),
        )


class LocalizationProperty(Base):
    """Store properties for localizations."""

    update = delete = AccessibleIfUserMatches('sent_by')

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this LocalizationProperty.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="localizationproperties",
        doc="The user that saved this LocalizationProperty",
    )

    localization_id = sa.Column(
        sa.ForeignKey('localizations.id', ondelete="CASCADE"),
        primary_key=True,
        index=True,
        doc='localization ID',
    )

    data = sa.Column(JSONB, doc="Localization properties in JSON format.", index=True)


class LocalizationTag(Base):
    """Store qualitative tags for localizations."""

    update = delete = AccessibleIfUserMatches('sent_by')

    sent_by_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this LocalizationTag.",
    )

    sent_by = relationship(
        "User",
        foreign_keys=sent_by_id,
        back_populates="localizationtags",
        doc="The user that saved this LocalizationTag",
    )

    localization_id = sa.Column(
        sa.ForeignKey('localizations.id', ondelete="CASCADE"),
        primary_key=True,
        index=True,
        doc='localization ID',
    )

    text = sa.Column(sa.Unicode, nullable=False, index=True)


# this doesnt work yet. It looks like the event is triggers, the code runs but the tables arent created/committed
# using postgresql code outside of skyportal, it did work however.
@event.listens_for(Localization, 'before_insert')
def localizationtile_before_insert(mapper, connection, target):
    partition_key = arrow.get(target.dateobs).datetime
    partition_name = f'localizationtiles_{partition_key.year}_{partition_key.month}'
    if partition_name not in LocalizationTile.partitions:
        print(f"creating partition {partition_name}")
        if partition_key.month == 12:
            LocalizationTile.create_partition(
                f"{partition_key.year}_{partition_key.month}",
                partition_stmt=f"""FOR VALUES FROM ('{partition_key.year}-{partition_key.month}-01') TO ('{partition_key.year+1}-01-01')""",
            )
        else:
            LocalizationTile.create_partition(
                f"{partition_key.year}_{partition_key.month}",
                partition_stmt=f"""FOR VALUES FROM ('{partition_key.year}-{partition_key.month}-01') TO ('{partition_key.year}-{partition_key.month+1}-01')""",
            )
