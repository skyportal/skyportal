# Customizations of baselayer User and Token models

from sqlalchemy.orm import relationship
from sqlalchemy import event

from slugify import slugify

from baselayer.app.models import (
    join_model,
    DBSession,
    User,
    Token,
    public,
    UserAccessControl,
    CustomUserAccessControl,
)

from .group import Group, GroupUser
from .followup_request import FollowupRequest
from .observation_plan import ObservationPlanRequest
from .stream import Stream
from .invitation import Invitation


def basic_user_display_info(user):
    return {
        field: getattr(user, field)
        for field in ('username', 'first_name', 'last_name', 'gravatar_url')
    }


def user_to_dict(self):
    return {
        field: getattr(self, field)
        for field in User.__table__.columns.keys()
        if field != "preferences"
    }


def user_update_delete_logic(cls, user_or_token):
    """A user can update or delete themselves, and a super admin can delete
    or update any user."""

    if user_or_token.is_admin:
        return public.query_accessible_rows(cls, user_or_token)

    # non admin users can only update or delete themselves
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)

    return DBSession().query(cls).filter(cls.id == user_id)


@property
def user_or_token_accessible_groups(self):
    """Return the list of Groups a User or Token has access to. For non-admin
    Users or Token owners, this corresponds to the Groups they are a member of.
    For System Admins, this corresponds to all Groups."""
    if "System admin" in self.permissions:
        return Group.query.all()
    return self.groups


@property
def user_or_token_accessible_streams(self):
    """Return the list of Streams a User or Token has access to."""
    if "System admin" in self.permissions:
        return Stream.query.all()
    if isinstance(self, Token):
        return self.created_by.streams
    return self.streams


User.to_dict = user_to_dict
User.accessible_groups = user_or_token_accessible_groups
User.accessible_streams = user_or_token_accessible_streams
User.single_user_group = property(
    lambda self: DBSession()
    .query(Group)
    .join(GroupUser)
    .filter(Group.single_user_group.is_(True), GroupUser.user_id == self.id)
    .first()
)
User.streams = relationship(
    'Stream',
    secondary='stream_users',
    back_populates='users',
    passive_deletes=True,
    doc="The Streams this User has access to.",
)
User.groups = relationship(
    'Group',
    secondary='group_users',
    back_populates='users',
    passive_deletes=True,
    doc="The Groups this User is a member of.",
)
User.shifts = relationship(
    'Shift',
    secondary='shift_users',
    back_populates='users',
    passive_deletes=True,
    doc="The Shifts this User is a member of.",
)
User.comments = relationship(
    "Comment",
    back_populates="author",
    foreign_keys="Comment.author_id",
    cascade="delete",
    passive_deletes=True,
)
User.annotations = relationship(
    "Annotation",
    back_populates="author",
    foreign_keys="Annotation.author_id",
    cascade="delete",
    passive_deletes=True,
)
User.photometry = relationship(
    'Photometry',
    doc='Photometry uploaded by this User.',
    back_populates='owner',
    passive_deletes=True,
    foreign_keys="Photometry.owner_id",
)
User.spectra = relationship(
    'Spectrum', doc='Spectra uploaded by this User.', back_populates='owner'
)
User.comments_on_spectra = relationship(
    "CommentOnSpectrum",
    back_populates="author",
    foreign_keys="CommentOnSpectrum.author_id",
    cascade="delete",
    passive_deletes=True,
)
User.annotations_on_spectra = relationship(
    "AnnotationOnSpectrum",
    back_populates="author",
    foreign_keys="AnnotationOnSpectrum.author_id",
    cascade="delete",
    passive_deletes=True,
)
User.comments_on_gcns = relationship(
    "CommentOnGCN",
    back_populates="author",
    foreign_keys="CommentOnGCN.author_id",
    cascade="delete",
    passive_deletes=True,
)
User.comments_on_shifts = relationship(
    "CommentOnShift",
    back_populates="author",
    foreign_keys="CommentOnShift.author_id",
    cascade="delete",
    passive_deletes=True,
)
User.followup_requests = relationship(
    'FollowupRequest',
    back_populates='requester',
    passive_deletes=True,
    doc="The follow-up requests this User has made.",
    foreign_keys=[FollowupRequest.requester_id],
)
User.observationplan_requests = relationship(
    'ObservationPlanRequest',
    back_populates='requester',
    passive_deletes=True,
    doc="The observation plan requests this User has made.",
    foreign_keys=[ObservationPlanRequest.requester_id],
)
User.transactions = relationship(
    'FacilityTransaction',
    back_populates='initiator',
    doc="The FacilityTransactions initiated by this User.",
    foreign_keys="FacilityTransaction.initiator_id",
)
User.assignments = relationship(
    'ClassicalAssignment',
    back_populates='requester',
    passive_deletes=True,
    doc="Objs the User has assigned to ObservingRuns.",
    foreign_keys="ClassicalAssignment.requester_id",
)
User.gcnevents = relationship(
    'GcnEvent',
    back_populates='sent_by',
    passive_deletes=True,
    doc='The gcnevents saved by this user',
)
User.gcnnotices = relationship(
    'GcnNotice',
    back_populates='sent_by',
    passive_deletes=True,
    doc='The GcnNotices saved by this user',
)
User.gcntags = relationship(
    'GcnTag',
    back_populates='sent_by',
    passive_deletes=True,
    doc='The gcntags saved by this user',
)
User.listings = relationship(
    'Listing',
    back_populates='user',
    passive_deletes=True,
    doc='The listings saved by this user',
)
User.localizations = relationship(
    'Localization',
    back_populates='sent_by',
    passive_deletes=True,
    doc='The localizations saved by this user',
)
User.notifications = relationship(
    "UserNotification",
    back_populates="user",
    passive_deletes=True,
    doc="Notifications to be displayed on front-end associated with User",
)
User.observing_runs = relationship(
    'ObservingRun',
    cascade='save-update, merge, refresh-expire, expunge',
    passive_deletes=True,
    doc="Observing Runs this User has created.",
    foreign_keys="ObservingRun.owner_id",
)
User.source_notifications = relationship(
    'SourceNotification',
    back_populates='sent_by',
    doc="Source notifications the User has sent out.",
    foreign_keys="SourceNotification.sent_by_id",
)
User.sources = relationship(
    'Obj',
    backref='users',
    secondary='join(Group, sources).join(group_users)',
    primaryjoin='group_users.c.user_id == users.c.id',
    doc='The Sources accessible to this User.',
    viewonly=True,
)

User.update = User.delete = CustomUserAccessControl(user_update_delete_logic)


@event.listens_for(User, 'after_insert')
def create_single_user_group(mapper, connection, target):

    # Create single-user group
    @event.listens_for(DBSession(), "after_flush", once=True)
    def receive_after_flush(session, context):
        session.add(
            Group(name=slugify(target.username), users=[target], single_user_group=True)
        )


@event.listens_for(User, 'before_delete')
def delete_single_user_group(mapper, connection, target):
    single_user_group = target.single_user_group

    # Delete single-user group
    @event.listens_for(DBSession(), "after_flush_postexec", once=True)
    def receive_after_flush(session, context):
        DBSession().delete(single_user_group)


@event.listens_for(User, 'after_update')
def update_single_user_group(mapper, connection, target):

    # Update single user group name if needed
    @event.listens_for(DBSession(), "after_flush_postexec", once=True)
    def receive_after_flush(session, context):
        single_user_group = target.single_user_group
        single_user_group.name = slugify(target.username)
        DBSession().merge(single_user_group)


@property
def isadmin(self):
    return "System admin" in self.permissions


User.is_system_admin = isadmin

UserInvitation = join_model("user_invitations", User, Invitation)


@property
def token_groups(self):
    """The groups the Token owner is a member of."""
    return self.created_by.groups


Token.groups = token_groups
Token.accessible_groups = user_or_token_accessible_groups
Token.accessible_streams = user_or_token_accessible_streams
Token.is_system_admin = isadmin
