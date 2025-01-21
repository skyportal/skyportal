__all__ = [
    "SpatialCatalog",
    "SpatialCatalogEntry",
    "SpatialCatalogEntryTile",
]

import healpix_alchemy
import healpy
import ligo.skymap.bayestar as ligo_bayestar
import numpy as np
import sqlalchemy as sa
from astropy.table import Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import deferred, relationship

from baselayer.app.models import Base


class SpatialCatalog(Base):
    """Spatial catalog information, composed of SpatialCatalogEntry's"""

    __tablename__ = "spatial_catalogs"

    catalog_name = sa.Column(
        sa.String, unique=True, nullable=False, doc="Name of the catalog.", index=True
    )

    entries = relationship(
        "SpatialCatalogEntry",
        cascade="save-update, merge, refresh-expire, expunge, delete",
        passive_deletes=True,
        order_by="SpatialCatalogEntry.entry_name",
        doc="Entries associated with this catalog.",
    )


class SpatialCatalogEntry(Base):
    """Spatial catalog entry"""

    __tablename__ = "spatial_catalog_entries"

    catalog_id = sa.Column(
        sa.ForeignKey("spatial_catalogs.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        doc="localization ID",
    )

    catalog = relationship(
        "SpatialCatalog",
        foreign_keys=catalog_id,
        back_populates="entries",
        doc="The SpatialCatalog that saved this SpatialCatalogEntry belongs to",
    )

    entry_name = sa.Column(
        sa.String, unique=True, nullable=False, doc="Entry name", index=True
    )

    data = sa.Column(
        JSONB,
        doc="Entry initialization properties in JSON format.",
        nullable=False,
        index=True,
    )

    nside = 512
    # HEALPix resolution used for flat (non-multiresolution) operations.

    uniq = deferred(
        sa.Column(
            sa.ARRAY(sa.BigInteger),
            nullable=False,
            doc="Multiresolution HEALPix UNIQ pixel index array",
        )
    )

    probdensity = deferred(
        sa.Column(
            sa.ARRAY(sa.Float),
            nullable=False,
            doc="Multiresolution HEALPix probability density array",
        )
    )

    @property
    def table(self):
        """Get multiresolution HEALPix dataset, probability density only."""
        return Table(
            [np.asarray(self.uniq, dtype=np.int64), self.probdensity],
            names=["UNIQ", "PROBDENSITY"],
        )

    @property
    def flat(self):
        """Get flat resolution HEALPix dataset, probability density only."""
        order = healpy.nside2order(SpatialCatalogEntry.nside)
        result = ligo_bayestar.rasterize(self.table, order)["PROB"]
        return healpy.reorder(result, "NESTED", "RING")


class SpatialCatalogEntryTile(Base):
    """This is a single tile within a catalog entry (as in the SpatialCatalogEntry table).
    Each tile has an associated healpix id and probability density."""

    __tablename__ = "spatial_catalog_entriess"

    entry_name = sa.Column(
        sa.ForeignKey("spatial_catalog_entries.entry_name", ondelete="CASCADE"),
        nullable=False,
        doc="Catalog entry name",
    )

    probdensity = sa.Column(
        sa.Float,
        nullable=False,
        index=True,
        doc="Probability density for the tile",
    )

    healpix = sa.Column(healpix_alchemy.Tile, primary_key=True, index=True)
