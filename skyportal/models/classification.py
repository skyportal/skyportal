__all__ = ['Classification']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, AccessibleIfUserMatches

from .group import accessible_by_groups_members
from .taxonomy import ok_if_tax_and_obj_readable


class Classification(Base):
    """Classification of an Obj."""

    create = ok_if_tax_and_obj_readable
    read = accessible_by_groups_members & ok_if_tax_and_obj_readable
    update = delete = AccessibleIfUserMatches('author')

    classification = sa.Column(
        sa.String, nullable=False, index=True, doc="The assigned class."
    )
    taxonomy_id = sa.Column(
        sa.ForeignKey('taxonomies.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Taxonomy in which this Classification was made.",
    )
    taxonomy = relationship(
        'Taxonomy',
        back_populates='classifications',
        doc="Taxonomy in which this Classification was made.",
    )
    probability = sa.Column(
        sa.Float,
        doc='User-assigned probability of belonging to this class',
        nullable=True,
        index=True,
    )

    author_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User that made this Classification",
    )
    author = relationship('User', doc="The User that made this classification.")
    author_name = sa.Column(
        sa.String,
        nullable=False,
        doc="User.username or Token.id " "of the Classification's author.",
    )
    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Classification's Obj.",
    )
    obj = relationship(
        'Obj', back_populates='classifications', doc="The Classification's Obj."
    )
    groups = relationship(
        "Group",
        secondary="group_classifications",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Groups that can access this Classification.",
    )
