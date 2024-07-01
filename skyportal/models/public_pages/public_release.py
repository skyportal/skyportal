__all__ = ['PublicRelease']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base


class PublicRelease(Base):
    """Public release of a group of sources."""

    id = sa.Column(sa.Integer, primary_key=True)

    name = sa.Column(
        sa.String,
        nullable=False,
        doc="Name of the public release",
    )

    link_name = sa.Column(
        sa.String,
        unique=True,
        nullable=False,
        doc="Name of the public release to be used in URLs",
    )

    description = sa.Column(
        sa.String,
        nullable=False,
        doc="Description of the public release",
    )

    is_visible = sa.Column(
        sa.Boolean,
        nullable=False,
        default=True,
        doc="Whether the public release is visible to the public",
    )

    groups = relationship(
        "Group",
        secondary="group_public_releases",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="The groups that can manage the public release",
    )

    source_pages = relationship(
        "PublicSourcePage",
        back_populates="release",
        doc="The source pages in this public release",
    )

    options = sa.Column(
        sa.JSON,
        nullable=False,
        doc="Default options for the public source of the release",
    )
