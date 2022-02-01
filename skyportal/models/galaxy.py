__all__ = ['Galaxy']

import sqlalchemy as sa
import conesearch_alchemy as ca
import healpix_alchemy

from baselayer.app.models import Base


class Galaxy(Base, ca.Point):
    """A record of a galaxy and its metadata, such as position,
    distance, name, and magnitude."""

    catalog_name = sa.Column(sa.String, nullable=False, doc="Name of the catalog.")

    name = sa.Column(sa.String, nullable=False, doc="Name of the object.")
    alt_name = sa.Column(
        sa.String, nullable=True, doc="Alternative Name of the object."
    )
    distmpc = sa.Column(sa.Float, nullable=True, doc="Distance [Mpc]")
    distmpc_unc = sa.Column(sa.Float, nullable=True, doc="Distance [Mpc] uncertainty")

    healpix = sa.Column(healpix_alchemy.Point, index=True)

    redshift = sa.Column(sa.Float, nullable=True, doc="Redshift.")
    redshift_error = sa.Column(sa.Float, nullable=True, doc="Redshift error.")

    sfr_fuv = sa.Column(sa.Float, nullable=True, doc="SFR based on FUV [Msol/yr]")
    mstar = sa.Column(sa.Float, nullable=True, doc="Stellar mass [log(Msol)]")
    magb = sa.Column(sa.Float, nullable=True, doc="B band magnitude [mag]")
    magk = sa.Column(sa.Float, nullable=True, doc="K band magnitude")
    a = sa.Column(sa.Float, nullable=True, doc="semi-major axis in arcsec [arcsec]")
    b2a = sa.Column(sa.Float, nullable=True, doc="semi-minor to semi-major axis ratio")
    pa = sa.Column(sa.Float, nullable=True, doc="position angle in degrees")
    btc = sa.Column(sa.Float, nullable=True, doc="total B-band magnitude [mag]")
