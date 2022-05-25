__all__ = [
    'GroupTaxonomy',
    'GroupComment',
    'GroupAnnotation',
    'GroupClassification',
    'GroupPhotometry',
    'GroupSpectrum',
    'GroupCommentOnSpectrum',
    'GroupCommentOnGCN',
    'GroupCommentOnShift',
    'GroupAnnotationOnSpectrum',
    'GroupInvitation',
    'GroupSourceNotification',
    'GroupStream',
]

import sqlalchemy as sa

from baselayer.app.models import join_model, User, AccessibleIfUserMatches

from baselayer.app.models import DBSession, restricted, CustomUserAccessControl
from .photometry import Photometry
from .taxonomy import Taxonomy
from .comment import Comment
from .annotation import Annotation
from .classification import Classification
from .spectrum import Spectrum
from .comment import CommentOnSpectrum
from .annotation import AnnotationOnSpectrum
from .comment import CommentOnGCN
from .comment import CommentOnShift
from .invitation import Invitation
from .source_notification import SourceNotification
from .filter import Filter
from .stream import Stream, StreamUser
from .group import Group, accessible_by_group_admins, accessible_by_group_members


GroupTaxonomy = join_model("group_taxonomy", Group, Taxonomy)
GroupTaxonomy.__doc__ = "Join table mapping Groups to Taxonomies."
GroupTaxonomy.delete = GroupTaxonomy.update = (
    accessible_by_group_admins & GroupTaxonomy.read
)

GroupComment = join_model("group_comments", Group, Comment)
GroupComment.__doc__ = "Join table mapping Groups to Comments."
GroupComment.delete = GroupComment.update = (
    accessible_by_group_admins & GroupComment.read
)

GroupAnnotation = join_model("group_annotations", Group, Annotation)
GroupAnnotation.__doc__ = "Join table mapping Groups to Annotation."
GroupAnnotation.delete = GroupAnnotation.update = (
    accessible_by_group_admins & GroupAnnotation.read
)

GroupClassification = join_model("group_classifications", Group, Classification)
GroupClassification.__doc__ = "Join table mapping Groups to Classifications."
GroupClassification.delete = GroupClassification.update = (
    accessible_by_group_admins & GroupClassification.read
)

GroupPhotometry = join_model("group_photometry", Group, Photometry)
GroupPhotometry.__doc__ = "Join table mapping Groups to Photometry."
GroupPhotometry.delete = GroupPhotometry.update = (
    accessible_by_group_admins & GroupPhotometry.read
)

GroupSpectrum = join_model("group_spectra", Group, Spectrum)
GroupSpectrum.__doc__ = 'Join table mapping Groups to Spectra.'
GroupSpectrum.update = GroupSpectrum.delete = (
    accessible_by_group_admins & GroupSpectrum.read
)

GroupCommentOnSpectrum = join_model(
    "group_comments_on_spectra", Group, CommentOnSpectrum
)
GroupCommentOnSpectrum.__doc__ = "Join table mapping Groups to CommentOnSpectrum."
GroupCommentOnSpectrum.delete = GroupCommentOnSpectrum.update = (
    accessible_by_group_admins & GroupCommentOnSpectrum.read
)

GroupAnnotationOnSpectrum = join_model(
    "group_annotations_on_spectra", Group, AnnotationOnSpectrum
)
GroupAnnotationOnSpectrum.__doc__ = "Join table mapping Groups to AnnotationOnSpectrum."
GroupAnnotationOnSpectrum.delete = GroupAnnotationOnSpectrum.update = (
    accessible_by_group_admins & GroupAnnotationOnSpectrum.read
)

GroupCommentOnGCN = join_model("group_comments_on_gcns", Group, CommentOnGCN)
GroupCommentOnGCN.__doc__ = "Join table mapping Groups to CommentOnGCN."
GroupCommentOnGCN.delete = GroupCommentOnGCN.update = (
    accessible_by_group_admins & GroupCommentOnGCN.read
)

GroupCommentOnShift = join_model("group_comments_on_shifts", Group, CommentOnShift)
GroupCommentOnShift.__doc__ = "Join table mapping Groups to CommentOnShift."
GroupCommentOnShift.delete = GroupCommentOnShift.update = (
    accessible_by_group_admins & GroupCommentOnShift.read
)

GroupInvitation = join_model('group_invitations', Group, Invitation)

GroupSourceNotification = join_model('group_notifications', Group, SourceNotification)
GroupSourceNotification.create = (
    GroupSourceNotification.read
) = accessible_by_group_members
GroupSourceNotification.update = (
    GroupSourceNotification.delete
) = accessible_by_group_admins | AccessibleIfUserMatches('sourcenotification.sent_by')

GroupStream = join_model('group_streams', Group, Stream)
GroupStream.__doc__ = "Join table mapping Groups to Streams."
GroupStream.update = restricted
GroupStream.delete = (
    # only admins can delete streams from groups
    accessible_by_group_admins
    & GroupStream.read
) & CustomUserAccessControl(
    # Can only delete a stream from the group if none of the group's filters
    # are operating on the stream.
    lambda cls, user_or_token: DBSession()
    .query(cls)
    .outerjoin(Stream)
    .outerjoin(
        Filter,
        sa.and_(Filter.stream_id == Stream.id, Filter.group_id == cls.group_id),
    )
    .group_by(cls.id)
    .having(
        sa.or_(
            sa.func.bool_and(Filter.id.is_(None)),
            sa.func.bool_and(Stream.id.is_(None)),  # group has no streams
        )
    )
)
GroupStream.create = (
    # only admins can add streams to groups
    accessible_by_group_admins
    & GroupStream.read
    & CustomUserAccessControl(
        # Can only add a stream to a group if all users in the group have
        # access to the stream.
        # Also, cannot add stream access to single user groups.
        lambda cls, user_or_token: DBSession()
        .query(cls)
        .join(Group, cls.group)
        .outerjoin(User, Group.users)
        .outerjoin(
            StreamUser,
            sa.and_(
                cls.stream_id == StreamUser.stream_id,
                User.id == StreamUser.user_id,
            ),
        )
        .filter(Group.single_user_group.is_(False))
        .group_by(cls.id)
        .having(
            sa.or_(
                sa.func.bool_and(StreamUser.stream_id.isnot(None)),
                sa.func.bool_and(User.id.is_(None)),
            )
        )
    )
)
