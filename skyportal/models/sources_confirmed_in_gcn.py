# this is the model of a table that has: a source id, a localization id, a flag to indicate if the source is confirmed or rejected

__all__ = ['SourcesConfirmedInGCN']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, CustomUserAccessControl, DBSession, public
from baselayer.app.env import load_env

_, cfg = load_env()


def manage_sources_confirmed_in_gcn_access_logic(cls, user_or_token):
    if user_or_token.is_admin or 'Manage GCNs' in user_or_token.permissions:
        return public.query_accessible_rows(cls, user_or_token)
    else:
        return DBSession().query(cls).filter(sa.false())


class SourcesConfirmedInGCN(Base):

    read = public
    create = update = delete = CustomUserAccessControl(
        manage_sources_confirmed_in_gcn_access_logic
    )

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc='ID of the Obj.',
    )

    obj = relationship(
        'Obj',
        back_populates='sources_in_gcns',
        doc='The assigned Obj.',
    )

    dateobs = sa.Column(
        sa.ForeignKey('gcnevents.dateobs', ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc='UTC event timestamp',
    )

    confirmed = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="If True, the source is confirmed in the GCN. If False, the source is rejected in the GCN."
        "If there is no row, the source is not yet confirmed or rejected in the GCN.",
    )
