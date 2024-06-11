__all__ = [
    'Localization',
    'LocalizationTag',
    'LocalizationProperty',
    'LocalizationTile',
]

import datetime

import dustmaps.sfd
import healpix_alchemy
import healpy
import ligo.skymap.distance
import ligo.skymap.moc
import ligo.skymap.bayestar as ligo_bayestar
import ligo.skymap.postprocess
import numpy as np
import sqlalchemy as sa
from astropy.table import Table
from dateutil.relativedelta import relativedelta
from dustmaps.config import config
from sqlalchemy import event, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import deferred, relationship
from sqlalchemy.sql.ddl import DDL

from baselayer.app.env import load_env
from baselayer.app.models import AccessibleIfUserMatches, Base
from baselayer.log import make_log

from ..utils.files import save_file_data, delete_file_data

_, cfg = load_env()
config['data_dir'] = cfg['misc.dustmap_folder']

log = make_log('models/localizations')

utcnow = func.timezone("UTC", func.current_timestamp())


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
        nullable=True,
        index=True,
        doc='UTC event timestamp',
    )

    moving_object_id = sa.Column(
        sa.ForeignKey('moving_objects.id', ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc='Associated moving object',
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

    _localization_path = sa.Column(
        sa.String,
        nullable=True,
        doc='file path where the data of the localization is saved.',
    )

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

    @property
    def marginal_moments(self):
        """Get marginalized distance information from the localization."""
        if self.is_3d:
            sky_map = self.table
            # Calculate the cumulative area in deg2 and the
            # cumulative probability.
            dA = ligo.skymap.moc.uniq2pixarea(sky_map['UNIQ'])
            dP = sky_map['PROBDENSITY'] * dA
            mu = sky_map['DISTMU']
            sigma = sky_map['DISTSIGMA']

            distmean, distsigma = ligo.skymap.distance.parameters_to_marginal_moments(
                dP, mu, sigma
            )
            return distmean, distsigma
        else:
            return None, None

    def get_localization_path(self):
        """
        Get the path to the localization's data.
        """
        return self._localization_path

    def save_data(self, filename, file_data):
        """
        Save the localization's data to disk.
        """

        # there's a default value but it is best to provide a full path in the config
        root_folder = cfg.get('localizations_folder', 'localizations_data')

        full_path = save_file_data(root_folder, str(self.id), filename, file_data)

        # persist the filename
        self._localization_path = full_path

    def delete_data(self):
        """
        Delete the localizations's data from disk.
        """

        try:
            delete_file_data(self._localization_path)

            # reset the filename
            self._localization_path = None
        except Exception:
            log(
                f"Failed to delete localization ID {self.id} file {self._localization_path}"
            )


class LocalizationTileMixin:
    """This is a single tile within a skymap (as in the Localization table).
    Each tile has an associated healpix id and probability density."""

    localization_id = sa.Column(
        sa.ForeignKey('localizations.id', ondelete='CASCADE'),
        primary_key=True,
        doc='localization ID',
    )

    probdensity = sa.Column(
        sa.Float,
        nullable=False,
        doc="Probability density for the tile",
    )

    dateobs = sa.Column(
        sa.DateTime,
        nullable=False,
        server_default=sa.text("'2023-01-01'::date"),
        primary_key=True,
        doc="Date of observation for the Localization to which this tile belongs",
    )

    healpix = sa.Column(healpix_alchemy.Tile, primary_key=True)


class LocalizationTile(
    Base,
    LocalizationTileMixin,
):
    created_at = sa.Column(
        sa.DateTime,
        nullable=False,
        default=utcnow,
        doc="UTC time of insertion of object's row into the database.",
    )

    __tablename__ = 'localizationtiles'
    __table_args__ = (
        sa.Index(
            'localizationtiles_id_dateobs_healpix_idx',
            'id',
            'dateobs',
            'healpix',
            unique=True,
        ),
        sa.Index(
            'localizationtiles_localization_id_idx',
            'localization_id',
            unique=False,
        ),
        sa.Index(
            'localizationtiles_probdensity_idx',
            'probdensity',
            unique=False,
        ),
        sa.Index(
            'localizationtiles_healpix_idx',
            'healpix',
            unique=False,
            postgresql_using="spgist",
        ),
        sa.Index(
            'localizationtiles_created_at_idx',
            'created_at',
            unique=False,
        ),
        {"postgresql_partition_by": "RANGE (dateobs)"},
    )

    partitions = {}

    @classmethod
    def create_partition(cls, name, partition_stmt, table_args=()):
        """Create a partition for the LocalizationTile table."""

        class Partition(Base, LocalizationTileMixin):
            created_at = sa.Column(
                sa.DateTime,
                nullable=False,
                default=utcnow,
                doc="UTC time of insertion of object's row into the database.",
            )
            __name__ = f'{cls.__name__}_{name}'
            __qualname__ = f'{cls.__qualname__}_{name}'
            __tablename__ = f'{cls.__tablename__}_{name}'
            __table_args__ = table_args

        event.listen(
            Partition.__table__,
            'after_create',
            DDL(
                f"""
                    ALTER TABLE {cls.__tablename__}
                    ATTACH PARTITION {Partition.__tablename__}
                    {partition_stmt};
                    """
            ),
        )

        cls.partitions[name] = Partition


# create default partition that will contain all data out of range
LocalizationTile.create_partition(
    "def",
    partition_stmt="DEFAULT",
    table_args=(
        sa.Index(
            'localizationtiles_def_id_dateobs_healpix_idx',
            'id',
            'dateobs',
            'healpix',
            unique=True,
        ),
        sa.Index(
            'localizationtiles_def_localization_id_idx',
            'localization_id',
            unique=False,
        ),
        sa.Index(
            'localizationtiles_def_probdensity_idx',
            'probdensity',
            unique=False,
        ),
        sa.Index(
            'localizationtiles_def_healpix_idx',
            'healpix',
            unique=False,
            postgresql_using="spgist",
        ),
        sa.Index(
            'localizationtiles_def_created_at_idx',
            'created_at',
            unique=False,
        ),
    ),
)

# create partitions from 2023-04-01 to 2025-04-01
for year in range(2023, 2026):
    for month in range(1 if year != 2023 else 4, 13 if year != 2025 else 5):
        date = datetime.date(year, month, 1)
        table_args = (
            sa.Index(
                f'localizationtiles_{date.strftime("%Y_%m")}_id_dateobs_healpix_idx',
                'id',
                'dateobs',
                'healpix',
                unique=True,
            ),
            sa.Index(
                f'localizationtiles_{date.strftime("%Y_%m")}_localization_id_idx',
                'localization_id',
                unique=False,
            ),
            sa.Index(
                f'localizationtiles_{date.strftime("%Y_%m")}_probdensity_idx',
                'probdensity',
                unique=False,
            ),
            sa.Index(
                f'localizationtiles_{date.strftime("%Y_%m")}_healpix_idx',
                'healpix',
                unique=False,
                postgresql_using="spgist",
            ),
            sa.Index(
                f'localizationtiles_{date.strftime("%Y_%m")}_created_at_idx',
                'created_at',
                unique=False,
            ),
        )

        LocalizationTile.create_partition(
            date.strftime("%Y_%m"),
            partition_stmt="FOR VALUES FROM ('{}') TO ('{}')".format(
                date.strftime("%Y-%m-%d"),
                (date + relativedelta(months=1)).strftime("%Y-%m-%d"),
            ),
            table_args=table_args,
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


@event.listens_for(Localization, 'after_delete')
def delete_localization_data_from_disk(mapper, connection, target):
    log(f'Deleting localization data for localization id={target.id}')
    target.delete_data()
