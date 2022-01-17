from baselayer.app.models import Base
import sqlalchemy as sa


class GenericPassband(Base):
    """Currently, we are restricted to the named passbands available in sncosmo. This allows the user to pass in a name, min_wavelength, and a max_wavelength to create a generic passband."""

    name = sa.Column(
        sa.String, unique=True, nullable=False, doc="Generic passband name."
    )

    min_wavelength = sa.Column(
        sa.Float, nullable=False, doc="Minimum wavelength of the generic passband."
    )

    max_wavelength = sa.Column(
        sa.Float, nullable=False, doc="Maximum wavelength of the generic passband."
    )
