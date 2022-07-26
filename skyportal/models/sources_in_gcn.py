# this is the model of a table that has: a source id, a localization id, a flag to indicate if the source is confirmed or rejected

__all__ = ['SourcesInGCN']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, CustomUserAccessControl, DBSession, public
from baselayer.app.env import load_env

_, cfg = load_env()


def manage_sourcesingcn_access_logic(cls, user_or_token):
    if user_or_token.is_admin or 'Manage GCNs' in user_or_token.permissions:
        return public.query_accessible_rows(cls, user_or_token)
    else:
        print("can't access")
        return DBSession().query(cls).filter(sa.false())


class SourcesInGCN(Base):

    read = public
    create = update = delete = CustomUserAccessControl(manage_sourcesingcn_access_logic)

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

    confirmed_or_rejected = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Confirmed",
    )
