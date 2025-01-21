__all__ = ["SourceLabel"]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import AccessibleIfRelatedRowsAreAccessible, Base

from .group import accessible_by_group_members


class SourceLabel(Base):
    """Record of an instance in which a Source was labelled (as noted
    by a checkmark from the User on the Source page).
    """

    create = read = update = delete = (
        accessible_by_group_members & AccessibleIfRelatedRowsAreAccessible(group="read")
    )

    obj_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        unique=False,
        index=True,
        doc="Object ID for which the labelling was registered.",
    )
    labeller_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User that made this SourceLabel",
    )
    labeller = relationship("User", doc="The User that labelled this source.")
    group_id = sa.Column(
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        index=True,
        doc="The ID of the Group the label is associated with.",
        nullable=False,
    )
    group = relationship(
        "Group",
        back_populates="source_labels",
        doc="The Group the label is associated with.",
    )
