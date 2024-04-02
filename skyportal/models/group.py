__all__ = [
    'AccessibleIfUserMatches',
    'AccessibleIfGroupUserIsAdminAndUserMatches',
    'Group',
    'GroupAdmissionRequest',
]

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    Base,
    DBSession,
    join_model,
    User,
    UserAccessControl,
    AccessibleIfUserMatches,
    CustomUserAccessControl,
    public,
    safe_aliased,
)
from baselayer.app.env import load_env


_, cfg = load_env()


# group admins can set the admin status of other group members
def groupuser_update_access_logic(cls, user_or_token):
    aliased = safe_aliased(cls)
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = DBSession().query(cls).join(aliased, cls.group_id == aliased.group_id)
    if not user_or_token.is_system_admin:
        query = query.filter(aliased.user_id == user_id, aliased.admin.is_(True))
    return query


class AccessibleIfGroupUserMatches(AccessibleIfUserMatches):
    def __init__(self, relationship_chain):
        """A class that grants access to users related to a specific GroupUser record
        through a chain of relationships pointing to a "groups.users" or "group.users"
        as the last two relationships.

        Parameters
        ----------
        relationship_chain: str
            The chain of relationships to check the User or Token against in
            `query_accessible_rows`. Should be specified as

            >>>> f'{relationship1_name}.{relationship2_name}...{relationshipN_name}'

            The first relationship should be defined on the target class, and
            each subsequent relationship should be defined on the class pointed
            to by the previous relationship. The final relationships should be a
            "groups.users" or "group.users" series.
        Examples
        --------

        Grant access if the querying user is a member of one of the target
        class's groups:

            >>>> AccessibleIfGroupUserMatches('groups.users')
        """
        self.relationship_chain = relationship_chain

    @property
    def relationship_key(self):
        return self._relationship_key

    @relationship_key.setter
    def relationship_chain(self, value):
        if not isinstance(value, str):
            raise ValueError(
                f'Invalid value for relationship key: {value}, expected str, got {value.__class__.__name__}'
            )
        relationship_names = value.split('.')
        if len(relationship_names) < 2:
            raise ValueError('Need at least 2 relationships to join on.')
        if relationship_names[-1] != 'users' and relationship_names[-2] not in [
            'group',
            'groups',
        ]:
            raise ValueError(
                'Relationship chain must end with "group.users" or "groups.users".'
            )
        self._relationship_key = value

    def query_accessible_rows(self, cls, user_or_token, columns=None):
        """Construct a Query object that, when executed, returns the rows of a
        specified table that are accessible to a specified user or token.

        Parameters
        ----------
        cls: `baselayer.app.models.DeclarativeMeta`
            The mapped class of the target table.
        user_or_token: `baselayer.app.models.User` or `baselayer.app.models.Token`
            The User or Token to check.
        columns: list of sqlalchemy.Column, optional, default None
            The columns to retrieve from the target table. If None, queries
            the mapped class directly and returns mapped instances.

        Returns
        -------
        query: sqlalchemy.Query
            Query for the accessible rows.
        """

        # system admins automatically get full access
        if user_or_token.is_admin:
            return public.query_accessible_rows(cls, user_or_token, columns=columns)

        # return only selected columns if requested
        if columns is not None:
            query = DBSession().query(*columns).select_from(cls)
        else:
            query = DBSession().query(cls).select_from(cls)

        # traverse the relationship chain via sequential JOINs
        for relationship_name in self.relationship_names:
            self.check_cls_for_attributes(cls, [relationship_name])
            relationship = sa.inspect(cls).mapper.relationships[relationship_name]
            # not a private attribute, just has an underscore to avoid name
            # collision with python keyword
            cls = relationship.entity.class_

            if str(relationship) == "Group.users":
                # For the last relationship between Group and User, just join
                # in the join table and not the join table and the full User table
                # since we only need the GroupUser.user_id field to match on
                query = query.join(GroupUser)
            else:
                query = query.join(relationship.class_attribute)

        # filter for records with at least one matching user
        user_id = self.user_id_from_user_or_token(user_or_token)
        query = query.filter(GroupUser.user_id == user_id)
        return query


class AccessibleIfGroupUserIsAdminAndUserMatches(AccessibleIfUserMatches):
    def __init__(self, relationship_chain):
        """A class that grants access to users related to a specific record
        through a chain of relationships. The relationship chain must
        contain a relationship called `group_users` and matches are only
        valid if the `admin` property of the corresponding `group_users` rows
        are true.
        Parameters
        ----------
        relationship_chain: str
            The chain of relationships to check the User or Token against in
            `query_accessible_rows`. Should be specified as

            >>>> f'{relationship1_name}.{relationship2_name}...{relationshipN_name}'

            The first relationship should be defined on the target class, and
            each subsequent relationship should be defined on the class pointed
            to by the previous relationship. If the querying user matches any
            record pointed to by the final relationship, the logic will grant
            access to the querying user.

        Examples
        --------

        Grant access if the querying user is an admin of any of the record's
        groups:

            >>>> AccessibleIfGroupUserIsAdminAndUserMatches('groups.group_users.user')

        Grant access if the querying user is an admin of the record's group:

            >>>> AccessibleIfUserMatches('group.group_users.user')
        """
        self.relationship_chain = relationship_chain

    @property
    def relationship_key(self):
        return self._relationship_key

    @relationship_key.setter
    def relationship_chain(self, value):
        if not isinstance(value, str):
            raise ValueError(
                f'Invalid value for relationship key: {value}, expected str, got {value.__class__.__name__}'
            )
        relationship_names = value.split('.')
        if 'group_users' not in value:
            raise ValueError('Relationship chain must contain "group_users".')
        if len(relationship_names) < 1:
            raise ValueError('Need at least 1 relationship to join on.')
        self._relationship_key = value

    def query_accessible_rows(self, cls, user_or_token, columns=None):
        """Construct a Query object that, when executed, returns the rows of a
        specified table that are accessible to a specified user or token.

        Parameters
        ----------
        cls: `baselayer.app.models.DeclarativeMeta`
            The mapped class of the target table.
        user_or_token: `baselayer.app.models.User` or `baselayer.app.models.Token`
            The User or Token to check.
        columns: list of sqlalchemy.Column, optional, default None
            The columns to retrieve from the target table. If None, queries
            the mapped class directly and returns mapped instances.

        Returns
        -------
        query: sqlalchemy.Query
            Query for the accessible rows.
        """

        query = super().query_accessible_rows(cls, user_or_token, columns=columns)
        if not user_or_token.is_admin:
            # this avoids name collisions
            group_user_subq = (
                DBSession()
                .query(GroupUser)
                .filter(GroupUser.admin.is_(True))
                .subquery()
            )
            query = query.join(
                group_user_subq,
                sa.and_(
                    Group.id == group_user_subq.c.group_id,
                    User.id == group_user_subq.c.user_id,
                ),
            )
        return query


accessible_by_group_admins = AccessibleIfGroupUserIsAdminAndUserMatches(
    'group.group_users.user'
)
accessible_by_groups_admins = AccessibleIfGroupUserIsAdminAndUserMatches(
    'groups.group_users.user'
)
accessible_by_admins = AccessibleIfGroupUserIsAdminAndUserMatches('group_users.user')
accessible_by_members = AccessibleIfUserMatches('users')
accessible_by_stream_members = AccessibleIfUserMatches('stream.users')
accessible_by_streams_members = AccessibleIfUserMatches('streams.users')
accessible_by_groups_members = AccessibleIfGroupUserMatches('groups.users')
accessible_by_group_members = AccessibleIfGroupUserMatches('group.users')


def delete_group_access_logic(cls, user_or_token):
    """User can delete a group that is not the sitewide public group, is not
    a single user group, and that they are an admin member of."""
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = (
        DBSession()
        .query(cls)
        .join(GroupUser)
        .filter(cls.name != cfg['misc']['public_group_name'])
        .filter(cls.single_user_group.is_(False))
    )
    if not user_or_token.is_system_admin:
        query = query.filter(GroupUser.user_id == user_id, GroupUser.admin.is_(True))
    return query


class Group(Base):
    """A user group. `Group`s controls `User` access to `Filter`s and serve as
    targets for data sharing requests. `Photometry` and `Spectra` shared with
    a `Group` will be visible to all its members. `Group`s maintain specific
    `Stream` permissions. In order for a `User` to join a `Group`, the `User`
    must have access to all of the `Group`'s data `Stream`s.
    """

    update = accessible_by_admins
    member = accessible_by_members

    # require group admin access for group deletion and do not allow
    # the public group to be deleted.
    delete = CustomUserAccessControl(delete_group_access_logic)

    name = sa.Column(
        sa.String, unique=True, nullable=False, index=True, doc='Name of the group.'
    )
    nickname = sa.Column(
        sa.String, unique=True, nullable=True, index=True, doc='Short group nickname.'
    )
    description = sa.Column(
        sa.Text, nullable=True, doc='Longer description of the group.'
    )
    private = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Boolean indicating whether group is invisible to non-members.",
    )
    streams = relationship(
        'Stream',
        secondary='group_streams',
        back_populates='groups',
        passive_deletes=True,
        doc='Stream access required for a User to become a member of the Group.',
    )
    filters = relationship(
        "Filter",
        back_populates="group",
        passive_deletes=True,
        doc='All filters (not just active) associated with a group.',
    )

    shifts = relationship(
        "Shift",
        back_populates="group",
        passive_deletes=True,
        doc='All shifts associated with a group.',
    )

    users = relationship(
        'User',
        secondary='group_users',
        back_populates='groups',
        passive_deletes=True,
        doc='The members of this group.',
    )

    group_users = relationship(
        'GroupUser',
        back_populates='group',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc='Elements of a join table mapping Users to Groups.',
        overlaps='users, groups',
    )

    observing_runs = relationship(
        'ObservingRun',
        back_populates='group',
        doc='The observing runs associated with this group.',
    )
    photometry = relationship(
        "Photometry",
        secondary="group_photometry",
        back_populates="groups",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='The photometry visible to this group.',
    )

    photometric_series = relationship(
        "PhotometricSeries",
        secondary="group_photometric_series",
        back_populates="groups",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='Photometric series visible to this group.',
    )

    spectra = relationship(
        "Spectrum",
        secondary="group_spectra",
        back_populates="groups",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='The spectra visible to this group.',
    )

    mmadetector_spectra = relationship(
        "MMADetectorSpectrum",
        secondary="group_mmadetector_spectra",
        back_populates="groups",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='The MMADetector spectra visible to this group.',
    )

    mmadetector_time_intervals = relationship(
        "MMADetectorTimeInterval",
        secondary="group_mmadetector_time_intervals",
        back_populates="groups",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='The MMADetector time intervals visible to this group.',
    )

    single_user_group = sa.Column(
        sa.Boolean,
        default=False,
        index=True,
        doc='Flag indicating whether this group '
        'is a singleton group for one user only.',
    )
    allocations = relationship(
        'Allocation',
        back_populates="group",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Allocations made to this group.",
    )
    source_labels = relationship(
        'SourceLabel',
        back_populates="group",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Source labels made by this group.",
    )
    admission_requests = relationship(
        "GroupAdmissionRequest",
        back_populates="group",
        passive_deletes=True,
        doc="User requests to join this group.",
    )
    tnsrobots = relationship(
        'TNSRobotGroup',
        back_populates="group",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="TNS Robots associated with this group.",
    )
    gcnreports = relationship(
        'GcnReport',
        back_populates="group",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Gcn Reports associated with this group.",
    )
    gcnsummaries = relationship(
        'GcnSummary',
        back_populates="group",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Gcn Summaries associated with this group.",
    )


GroupUser = join_model('group_users', Group, User)
GroupUser.__doc__ = "Join table mapping `Group`s to `User`s."
GroupUser.admin = sa.Column(
    sa.Boolean,
    nullable=False,
    default=False,
    doc="Boolean flag indicating whether the User is an admin of the group.",
)
GroupUser.can_save = sa.Column(
    sa.Boolean,
    nullable=False,
    server_default="true",
    doc="Boolean flag indicating whether the user should be able to save sources to the group",
)
GroupUser.update = CustomUserAccessControl(groupuser_update_access_logic)
GroupUser.delete = (
    # users can remove themselves from a group
    # admins can remove users from a group
    # no one can remove a user from their single user group
    (accessible_by_group_admins | AccessibleIfUserMatches('user'))
    & GroupUser.read
    & CustomUserAccessControl(
        lambda cls, user_or_token: DBSession()
        .query(cls)
        .join(Group)
        .filter(Group.single_user_group.is_(False))
    )
)


def group_create_logic(cls, user_or_token):
    """
    Can only add a user to a group if they have all the requisite
    streams required for entry to the group. And users cannot
    be added to single user groups through the Groups API (only
    through event handlers).
    """
    from .stream import Stream, StreamUser

    return (
        DBSession()
        .query(cls)
        .join(Group)
        .outerjoin(Stream, Group.streams)
        .outerjoin(
            StreamUser,
            sa.and_(
                StreamUser.user_id == cls.user_id,
                StreamUser.stream_id == Stream.id,
            ),
        )
        .filter(Group.single_user_group.is_(False))
        .group_by(cls.id)
        .having(
            sa.or_(
                sa.func.bool_and(StreamUser.stream_id.isnot(None)),
                sa.func.bool_and(Stream.id.is_(None)),  # group has no streams
            )
        )
    )


GroupUser.create = (
    GroupUser.read
    # only admins can add people to groups
    & accessible_by_group_admins
    & CustomUserAccessControl(group_create_logic)
)

User.group_admission_requests = relationship(
    "GroupAdmissionRequest",
    back_populates="user",
    passive_deletes=True,
    doc="User's requests to join groups.",
)


class GroupAdmissionRequest(Base):
    """Table tracking requests from users to join groups."""

    read = AccessibleIfUserMatches('user') | accessible_by_group_admins
    create = delete = AccessibleIfUserMatches('user')
    update = accessible_by_group_admins

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the User requesting to join the group",
    )
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="group_admission_requests",
        doc="The User requesting to join a group",
    )
    group_id = sa.Column(
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the Group to which admission is requested",
    )
    group = relationship(
        "Group",
        foreign_keys=[group_id],
        back_populates="admission_requests",
        doc="The Group to which admission is requested",
    )
    status = sa.Column(
        sa.Enum(
            "pending",
            "accepted",
            "declined",
            name="admission_request_status",
            validate_strings=True,
        ),
        nullable=False,
        default="pending",
        doc=(
            "Admission request status. Can be one of either 'pending', "
            "'accepted', or 'declined'."
        ),
    )
