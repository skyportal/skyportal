__all__ = ["SourcesConfirmedInGCN"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.env import load_env
from baselayer.app.models import Base, CustomUserAccessControl, DBSession, public

_, cfg = load_env()


def manage_sources_confirmed_in_gcn_access_logic(cls, user_or_token):
    if user_or_token.is_admin or "Manage GCNs" in user_or_token.permissions:
        return public.query_accessible_rows(cls, user_or_token)
    else:
        return DBSession().query(cls).filter(sa.false())


class SourcesConfirmedInGCN(Base):
    read = public
    create = update = delete = CustomUserAccessControl(
        manage_sources_confirmed_in_gcn_access_logic
    )

    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Obj.",
    )

    obj = relationship(
        "Obj",
        back_populates="sources_in_gcns",
        doc="The assigned Obj.",
    )

    dateobs = sa.Column(
        sa.ForeignKey("gcnevents.dateobs", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="UTC event timestamp",
    )

    confirmed = sa.Column(
        sa.Boolean,
        doc="If True, the source is confirmed in the GCN. If False, the source is rejected in the GCN."
        "If undefined, the source is not yet confirmed or rejected in the GCN.",
    )

    # the person who uploaded the confirmation
    confirmer = relationship(
        "User",
        back_populates="sources_in_gcn",
        doc="The User who created this SourcesConfirmedInGCN.",
        foreign_keys="SourcesConfirmedInGCN.confirmer_id",
    )
    confirmer_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The ID of the User who created this SourcesConfirmedInGCN.",
    )

    explanation = sa.Column(
        sa.String,
        doc="Explanation on the nature of confirmation or rejection.",
    )

    notes = sa.Column(
        sa.String,
        doc="Extra information about the source.",
    )
