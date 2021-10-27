__all__ = ['Galaxy']

import sqlalchemy as sa
import healpix_alchemy as ha

from baselayer.app.models import Base


class Galaxy(Base, ha.Point):
    """A record of a galaxy and its metadata, such as position,
    distance, name, and magnitude."""

    catalog_name = sa.Column(sa.String, doc="Name of the catalog.")

    name = sa.Column(sa.String, doc="Name of the object.")
    distmpc = sa.Column(sa.Float, nullable=True, doc="Distance [Mpc]")
    sfr_fuv = sa.Column(sa.Float, nullable=True, doc="SFR based on FUV [Msol/yr]")
    mstar = sa.Column(sa.Float, nullable=True, doc="Stellar mass [log(Msol)]")
    magb = sa.Column(sa.Float, nullable=True, doc="B band magnitude [mag]")
    a = sa.Column(sa.Float, nullable=True, doc="semi-major axis in arcsec [arcsec]")
    b2a = sa.Column(sa.Float, nullable=True, doc="semi-minor to semi-major axis ratio")
    pa = sa.Column(sa.Float, nullable=True, doc="position angle in degrees")
    btc = sa.Column(sa.Float, nullable=True, doc="total B-band magnitude [mag]")
