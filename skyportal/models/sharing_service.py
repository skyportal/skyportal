__all__ = [
    "SharingService",
    "SharingServiceCoauthor",
    "SharingServiceGroup",
    "SharingServiceGroupAutoPublisher",
    "SharingServicesSubmission",
]

import json

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.orm import column_property, deferred, relationship
from sqlalchemy_utils.types import JSONType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine, EncryptedType

from baselayer.app.env import load_env
from baselayer.app.models import (
    Base,
    CustomUserAccessControl,
    UserAccessControl,
)

from .group import Group, GroupUser

_, cfg = load_env()


class SharingService(Base):
    """A bot that can publish to external services."""

    name = sa.Column(sa.String, unique=True, nullable=False, doc="Bot name.")

    instruments = relationship(
        "Instrument",
        secondary="instrument_sharingservices",
        back_populates="sharing_services",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Instruments to restrict the photometry to when publishing.",
    )

    streams = relationship(
        "Stream",
        secondary="stream_sharingservices",
        back_populates="sharing_services",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Streams to restrict the photometry to when publishing.",
    )

    acknowledgments = sa.Column(
        sa.String,
        nullable=False,
        server_default="",
        doc="Acknowledgments to use for this bot.",
    )

    testing = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="true",
        doc="If true, bot will not publish to external services and only store the request's payload.",
    )

    photometry_options = sa.Column(
        psql.JSONB,
        nullable=True,
        doc="Photometry options to use for this bot, to make some data optional or mandatory for manual and auto-publishing.",
    )

    enable_sharing_with_hermes = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="Whether to enable publishing to Hermes or not.",
    )

    enable_sharing_with_tns = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="true",
        doc="Whether to enable publishing to TNS or not.",
    )

    # Fields specific to TNS
    tns_bot_name = sa.Column(sa.String, doc="Name of the TNS bot.", nullable=True)
    tns_bot_id = sa.Column(sa.Integer, doc="ID of the TNS bot.", nullable=True)
    tns_source_group_id = sa.Column(
        sa.Integer, doc="Source group ID of the TNS bot.", nullable=True
    )
    _tns_altdata = sa.Column(
        EncryptedType(JSONType, cfg["app.secret_key"], AesEngine, "pkcs5")
    )
    publish_existing_tns_objects = sa.Column(
        sa.Boolean,
        nullable=True,
        server_default="false",
        doc="Whether to publish objects that already exist in TNS but not reported under this internal name (e.g., reported by another survey).",
    )

    @property
    def tns_altdata(self):
        if self._tns_altdata is None:
            return {}
        else:
            return json.loads(self._tns_altdata)

    @tns_altdata.setter
    def tns_altdata(self, value):
        self._tns_altdata = value

    groups = relationship(
        "SharingServiceGroup",
        back_populates="sharingservices",
        passive_deletes=True,
        doc="Groups associated with this sharing service.",
    )

    coauthors = relationship(
        "SharingServiceCoauthor",
        back_populates="sharingservices",
        passive_deletes=True,
        doc="Coauthors associated with this sharing service.",
    )


class SharingServiceCoauthor(Base):
    """Coauthors for external sharing services."""

    sharingservice_id = sa.Column(
        sa.ForeignKey(
            "sharingservices.id",
            name="bot_coauthors_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    user_id = sa.Column(sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    sharingservices = relationship(
        "SharingService",
        back_populates="coauthors",
        doc="The SharingServices associated with this mapper.",
    )


# unique constraint on the sharing_service_id and user_id columns
SharingServiceCoauthor.__table_args__ = (
    sa.UniqueConstraint("sharingservice_id", "user_id"),
)


class SharingServiceGroup(Base):
    """Mapper between SharingServices and Groups."""

    sharingservice_id = sa.Column(
        sa.ForeignKey(
            "sharingservices.id",
            name="bot_groups_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    group_id = sa.Column(sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)

    owner = sa.Column(sa.Boolean, nullable=False, default=False)
    auto_share_to_tns = sa.Column(sa.Boolean, nullable=False, server_default="false")
    auto_share_to_hermes = sa.Column(sa.Boolean, nullable=False, server_default="false")
    auto_sharing_allow_bots = sa.Column(
        sa.Boolean, nullable=False, server_default="false"
    )

    sharingservices = relationship(
        "SharingService",
        back_populates="groups",
        doc="The SharingService associated with this mapper.",
    )

    group = relationship(
        "Group",
        back_populates="sharing_services",
        doc="The Group associated with this mapper.",
    )

    auto_publishers = relationship(
        "SharingServiceGroupAutoPublisher",
        back_populates="sharingservicegroups",
        passive_deletes=True,
        doc="Users associated with this SharingServiceGroup.",
    )


# we want a unique index on the sharing_service_id and group_id columns
SharingServiceGroup.__table_args__ = (
    sa.UniqueConstraint("sharingservice_id", "group_id"),
)


class SharingServiceGroupAutoPublisher(Base):
    """Mapper between SharingServices and Users that are allowed to auto-publish."""

    sharingservices_group_id = sa.Column(
        sa.ForeignKey(
            "sharingservicegroups.id",
            name="bot_group_users_bot_group_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    group_user_id = sa.Column(
        sa.ForeignKey("group_users.id", ondelete="CASCADE"), nullable=False
    )

    sharingservicegroups = relationship(
        "SharingServiceGroup",
        back_populates="auto_publishers",
        doc="The SharingService associated with this mapper.",
    )


# we want a unique index on the sharing_service_id and group_user_id columns
SharingServiceGroupAutoPublisher.__table_args__ = (
    sa.UniqueConstraint("sharingservices_group_id", "group_user_id"),
)

# we add a method that gives us the user_id from that group_user
SharingServiceGroupAutoPublisher.user_id = column_property(
    sa.select(GroupUser.user_id)
    .where(GroupUser.id == SharingServiceGroupAutoPublisher.group_user_id)
    .scalar_subquery()
)


class SharingServicesSubmission(Base):
    """Objects to be auto-submitted."""

    sharingservice_id = sa.Column(
        sa.ForeignKey(
            "sharingservices.id",
            name="submissions_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    obj_id = sa.Column(sa.ForeignKey("objs.id", ondelete="CASCADE"), nullable=False)
    user_id = sa.Column(sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    custom_publishing_string = sa.Column(
        sa.String,
        nullable=True,
        default=None,
        doc="Custom publishing string to use for this submission only.",
    )
    custom_remarks_string = sa.Column(
        sa.String,
        nullable=True,
        default=None,
        doc="Custom remarks string to use for this submission only.",
    )

    publish_to_tns = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="Whether to publish to TNS or not.",
    )

    tns_status = sa.Column(
        sa.String, nullable=True, doc="Status of the TNS submission."
    )

    tns_submission_id = sa.Column(
        sa.Integer,
        nullable=True,
        default=None,
        doc="ID of the submission returned by TNS.",
    )

    tns_response = deferred(
        sa.Column(psql.JSONB, doc="Serialized HTTP response from TNS.")
    )

    tns_payload = deferred(sa.Column(psql.JSONB, doc="Payload to publish to TNS."))

    publish_to_hermes = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="Whether to publish to Hermes or not.",
    )

    hermes_status = sa.Column(
        sa.String, nullable=True, doc="Status of the Hermes submission."
    )

    hermes_response = deferred(
        sa.Column(psql.JSONB, doc="Serialized HTTP response from Hermes.")
    )

    archival = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Whether this is an archival submission or not.",
    )

    archival_comment = sa.Column(
        sa.String,
        nullable=True,
        default=None,
        doc="Comment to use for archival submission.",
    )

    auto_submission = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Whether this submission was auto-requested or not.",
    )

    instrument_ids = sa.Column(
        sa.ARRAY(sa.Integer),
        nullable=True,
        default=None,
        doc="Instrument IDs to use for this submission. If specified, overrides the bot's default instrument IDs.",
    )

    stream_ids = sa.Column(
        sa.ARRAY(sa.Integer),
        nullable=True,
        default=None,
        doc="Stream IDs to use for this submission. If specified, overrides the bot's default stream IDs.",
    )

    photometry_options = sa.Column(
        psql.JSONB,
        nullable=True,
        doc="Photometry options to use for this submission, to make some data optional or mandatory."
        "If specified, overrides the bot's default photometry options.",
    )

    sharingservices = relationship(
        "SharingService",
        back_populates="submissions",
        doc="The SharingService associated with this mapper.",
    )

    obj = relationship(
        "Obj",
        back_populates="sharing_service_submissions",
        doc="The Obj associated with this mapper.",
    )

    user = relationship(
        "User",
        back_populates="sharing_service_submissions",
        doc="The User associated with this mapper.",
    )


SharingService.submissions = relationship(
    "SharingServicesSubmission",
    back_populates="sharingservices",
    passive_deletes=True,
    doc="Auto-submissions associated with this SharingService.",
)


def sharing_service_read_access_logic(cls, user_or_token):
    """Return a query that filters SharingService instances based on user read access."""
    # if the user is a system admin, they can see all SharingServices
    # otherwise, they can only see SharingServices that are associated with groups they are in
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.join(SharingServiceGroup)
        query = query.where(
            SharingServiceGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            )
        )
    return query


def sharing_service_update_delete_access_logic(cls, user_or_token):
    """Return a query that filters SharingService instances based on user update/delete access."""
    # same as read access, but at least one of the groups must be an owner of the SharingService
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.join(SharingServiceGroup)
        query = query.where(
            SharingServiceGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            ),
            SharingServiceGroup.owner.is_(True),
        )
    return query


SharingService.read = CustomUserAccessControl(sharing_service_read_access_logic)
SharingService.update = SharingService.delete = CustomUserAccessControl(
    sharing_service_update_delete_access_logic
)


def sharing_service_coauthor_read_access_logic(cls, user_or_token):
    """Return a query that filters SharingServiceCoauthor instances based on user read access."""
    # if the user is a system admin, they can see all SharingServiceCoauthors
    # otherwise, they can only see SharingServiceCoauthors from SharingServices that are associated with groups they are in
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.where(
            SharingServiceCoauthor.sharingservice_id.in_(
                sa.select(SharingServiceGroup.sharingservice_id).where(
                    SharingServiceGroup.group_id.in_(
                        sa.select(GroupUser.group_id).where(
                            GroupUser.user_id == user_id
                        )
                    ),
                )
            ),
        )
    return query


def sharing_service_coauthor_create_update_delete_access_logic(cls, user_or_token):
    """Return a query that filters SharingServiceCoauthor instances based on user create/update/delete access."""
    # same as read access, but at least one of the groups must be an owner of the SharingService
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.where(
            SharingServiceCoauthor.sharingservice_id.in_(
                sa.select(SharingServiceGroup.sharingservice_id).where(
                    SharingServiceGroup.group_id.in_(
                        sa.select(GroupUser.group_id).where(
                            GroupUser.user_id == user_id
                        )
                    ),
                    SharingServiceGroup.owner.is_(True),
                )
            ),
        )
    return query


SharingServiceCoauthor.read = CustomUserAccessControl(
    sharing_service_coauthor_read_access_logic
)

SharingServiceCoauthor.create = SharingServiceCoauthor.update = (
    SharingServiceCoauthor.delete
) = CustomUserAccessControl(sharing_service_coauthor_create_update_delete_access_logic)


def sharing_service_group_read_access_logic(cls, user_or_token):
    """Return a query that filters SharingServiceGroup instances based on user read access."""
    # if the user is a system admin, they can see all SharingServiceGroups
    # otherwise, they can only see SharingServiceGroups that are associated with groups they are in
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        # a user should only be able to read SharingServiceGroups that are associated with groups
        # to which they have access
        query = query.where(
            SharingServiceGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            )
        )
    return query


def sharing_service_group_create_update_delete_access_logic(cls, user_or_token):
    """Return a query that filters SharingServiceGroup instances based on user create/update/delete access."""
    # same as read access, but at least one of the groups must be an owner of the SharingService
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        # 1. the user has access to the group
        # 2. the user has access to any group that is associated with the bot as an owner
        query = query.where(
            SharingServiceGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            ),
            SharingServiceGroup.sharingservice_id.in_(
                sa.select(SharingServiceGroup.sharingservice_id).where(
                    SharingServiceGroup.group_id.in_(
                        sa.select(GroupUser.group_id).where(
                            GroupUser.user_id == user_id
                        )
                    ),
                    SharingServiceGroup.owner.is_(True),
                )
            ),
        )
    return query


SharingServiceGroup.read = CustomUserAccessControl(
    sharing_service_group_read_access_logic
)
SharingServiceGroup.create = SharingServiceGroup.update = SharingServiceGroup.delete = (
    CustomUserAccessControl(sharing_service_group_create_update_delete_access_logic)
)

# for the SharingServiceGroupAutoPublisher, we will use the same access logic as for SharingServiceGroup
SharingServiceGroupAutoPublisher.read = CustomUserAccessControl(
    sharing_service_read_access_logic
)
SharingServiceGroupAutoPublisher.create = SharingServiceGroupAutoPublisher.update = (
    SharingServiceGroupAutoPublisher.delete
) = CustomUserAccessControl(sharing_service_update_delete_access_logic)


def sharing_service_submission_access_logic(cls, user_or_token):
    """Return a query that filters SharingServicesSubmission instances based on user read/create/update/delete access."""
    # if the user is a system admin, they can create/read/update/delete all SharingServicesSubmissions
    # otherwise, they can do so only using SharingServices that are associated with groups they are in
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.where(
            SharingServicesSubmission.sharingservice_id.in_(
                sa.select(SharingService.id)
                .join(SharingServiceGroup)
                .join(Group)
                .join(GroupUser)
                .where(GroupUser.user_id == user_id)
            )
        )
    return query


SharingServicesSubmission.read = SharingServicesSubmission.create = (
    SharingServicesSubmission.update
) = SharingServicesSubmission.delete = CustomUserAccessControl(
    sharing_service_submission_access_logic
)
