__all__ = ['Classification', 'ClassificationVote']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    Base,
    AccessibleIfUserMatches,
    AccessibleIfRelatedRowsAreAccessible,
)

from .group import accessible_by_groups_members, accessible_by_groups_admins
from .taxonomy import ok_if_tax_and_obj_readable


class Classification(Base):
    """Classification of an Obj."""

    create = ok_if_tax_and_obj_readable
    read = accessible_by_groups_members & ok_if_tax_and_obj_readable
    update = delete = accessible_by_groups_admins | AccessibleIfUserMatches('author')

    classification = sa.Column(
        sa.String, nullable=False, index=True, doc="The assigned class."
    )
    origin = sa.Column(
        sa.String,
        nullable=True,
        index=True,
        doc="String describing the source of this classification.",
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
    ml = sa.Column(
        sa.Boolean,
        doc='Whether this classification was made by a machine learning algorithm, or a human',
        nullable=False,
        server_default='false',
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
    votes = relationship(
        'ClassificationVote',
        back_populates="classification",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Classification votes for this classification.",
    )

    def to_dict_public(self):
        return {
            'classification': self.classification,
            'author_name': self.author_name,
            'probability': self.probability,
            'ml': self.ml,
            'taxname': self.taxonomy.name if self.taxonomy else None,
        }


class ClassificationVote(Base):
    """Record of an instance in which a Classification is voted up or down
    (as noted by thumbs up or down from the User on the Source page).
    """

    create = read = update = delete = AccessibleIfRelatedRowsAreAccessible(
        classification='read'
    )

    classification_id = sa.Column(
        sa.ForeignKey('classifications.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True,
        doc="Object ID for which the vote was registered.",
    )
    classification = relationship(
        'Classification',
        back_populates='votes',
        doc='The Classification the vote is associated with.',
    )
    voter_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User that made this ClassificationVote",
    )
    voter = relationship('User', doc="The User that scanned this source.")
    vote = sa.Column(
        sa.Integer,
        doc='User-assigned vote for classification (will generally be 1 for upvote and -1 for downvote)',
        nullable=False,
        index=True,
    )
