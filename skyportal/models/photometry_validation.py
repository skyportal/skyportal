# this is the model of a table that has: a photometry id, a flag to indicate if the photometry is validated or not

__all__ = ['PhotometryValidation']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, CustomUserAccessControl, DBSession, public
from baselayer.app.env import load_env

_, cfg = load_env()


def manage_photometry_validation_access_logic(cls, user_or_token):
    if user_or_token.is_admin or 'Manage sources' in user_or_token.permissions:
        return public.query_accessible_rows(cls, user_or_token)
    else:
        return DBSession().query(cls).filter(sa.false())


class PhotometryValidation(Base):
    read = public
    create = update = delete = CustomUserAccessControl(
        manage_photometry_validation_access_logic
    )

    photometry_id = sa.Column(
        sa.ForeignKey('photometry.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Annotation's Photometry.",
    )
    photometry = relationship(
        'Photometry',
        back_populates='validations',
        doc="The Photometry referred to by this validation.",
    )

    validated = sa.Column(
        sa.Boolean,
        doc="If True, the photometry is confirmed to be valid. If False, the photometry is deemed unreliable."
        "If undefined, the photometry is not yet validated or deemed unreliable.",
    )

    validator_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the User who created this PhotometryValidation.",
    )

    explanation = sa.Column(
        sa.String,
        doc="Explanation on the nature of validation vs rejection.",
    )

    notes = sa.Column(
        sa.String,
        doc="Extra information about the photometry.",
    )
