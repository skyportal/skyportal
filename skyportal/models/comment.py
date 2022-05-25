__all__ = [
    'Comment',
    'CommentOnSpectrum',
    'CommentOnGCN',
    'CommentOnShift',
]

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    Base,
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
)

from .group import accessible_by_groups_members


"""
NOTE ON ADDING NEW COMMENT TYPES:
To add a new comment on <something> you need to
- Inherit from CommentMixin (as well as Base).
- Add the name of the table to backref_name on CommentMixin
- Add any additional columns, like references to a model the comment is on.
- Add the comment as a relationship with back_populates (etc.) on the model you are commenting on.
  (e.g., for CommentOnSpectrum you need to add "comments" to models/spectrum.py)
- Add a join to models/group_joins.py so comments will have groups associated with them.
- Add a join to models/user_token.py so comments will have a user associated with them.
- Update the API endpoints for comments, and the reducers to listen for changes in the comments.
- Update the app_server.py paths to accept the new type of comment upon API calls.

"""


class CommentMixin:
    text = sa.Column(sa.String, nullable=False, doc="Comment body.")

    attachment_name = sa.Column(
        sa.String, nullable=True, doc="Filename of the attachment."
    )

    attachment_bytes = sa.Column(
        sa.types.LargeBinary,
        nullable=True,
        doc="Binary representation of the attachment.",
    )

    origin = sa.Column(sa.String, nullable=True, doc='Comment origin.')

    bot = sa.Column(
        sa.Boolean(),
        nullable=False,
        server_default="false",
        doc="Boolean indicating whether comment was posted via a bot (token-based request).",
    )

    @classmethod
    def backref_name(cls):
        if cls.__name__ == 'Comment':
            return "comments"
        if cls.__name__ == 'CommentOnSpectrum':
            return 'comments_on_spectra'
        if cls.__name__ == 'CommentOnGCN':
            return 'comments_on_gcns'
        if cls.__name__ == 'CommentOnShift':
            return 'comments_on_shifts'

    @declared_attr
    def author(cls):
        return relationship(
            "User",
            back_populates=cls.backref_name(),
            doc="Comment's author.",
            uselist=False,
            foreign_keys=f"{cls.__name__}.author_id",
        )

    @declared_attr
    def author_id(cls):
        return sa.Column(
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the Comment author's User instance.",
        )

    @declared_attr
    def groups(cls):
        return relationship(
            "Group",
            secondary="group_" + cls.backref_name(),
            cascade="save-update, merge, refresh-expire, expunge",
            passive_deletes=True,
            doc="Groups that can see the comment.",
        )

    def construct_author_info_dict(self):
        return {
            field: getattr(self.author, field)
            for field in ('username', 'first_name', 'last_name', 'gravatar_url')
        }


class Comment(Base, CommentMixin):
    """A comment made by a User or a Robot (via the API) on a Source."""

    create = AccessibleIfRelatedRowsAreAccessible(obj='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        obj='read'
    )

    update = delete = AccessibleIfUserMatches('author')

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Comment's Obj.",
    )

    obj = relationship(
        'Obj',
        back_populates='comments',
        doc="The Comment's Obj.",
    )


class CommentOnSpectrum(Base, CommentMixin):

    __tablename__ = 'comments_on_spectra'

    create = AccessibleIfRelatedRowsAreAccessible(obj='read', spectrum='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        obj='read',
        spectrum='read',
    )

    update = delete = AccessibleIfUserMatches('author')

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Comment's Obj.",
    )

    obj = relationship(
        'Obj',
        back_populates='comments_on_spectra',
        doc="The Comment's Obj.",
    )

    spectrum_id = sa.Column(
        sa.ForeignKey('spectra.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Comment's Spectrum.",
    )
    spectrum = relationship(
        'Spectrum',
        back_populates='comments',
        doc="The Spectrum referred to by this comment.",
    )


class CommentOnGCN(Base, CommentMixin):

    __tablename__ = 'comments_on_gcns'

    create = AccessibleIfRelatedRowsAreAccessible(gcn='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        gcn='read',
    )

    update = delete = AccessibleIfUserMatches('author')

    gcn_id = sa.Column(
        sa.ForeignKey('gcnevents.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Comment's GCN.",
    )
    gcn = relationship(
        'GcnEvent',
        back_populates='comments',
        doc="The GcnEvent referred to by this comment.",
    )


class CommentOnShift(Base, CommentMixin):

    __tablename__ = 'comments_on_shifts'

    create = AccessibleIfRelatedRowsAreAccessible(shift='read')

    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        shift='read',
    )

    update = delete = AccessibleIfUserMatches('author')

    shift_id = sa.Column(
        sa.ForeignKey('shifts.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Comment's Shift.",
    )
    shift = relationship(
        'Shift',
        back_populates='comments',
        doc="The Shift referred to by this comment.",
    )
