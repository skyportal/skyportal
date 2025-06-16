__all__ = [
    "ExternalPublishingBot",
    "ExternalPublishingBotCoauthor",
    "ExternalPublishingBotGroup",
    "ExternalPublishingBotGroupAutoPublisher",
    "ExternalPublishingSubmission",
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


class ExternalPublishingBot(Base):
    """A bot that can publish to external services."""

    __tablename__ = "external_publishing_bots"

    bot_name = sa.Column(sa.String, doc="Name of the bot.", nullable=False)

    instruments = relationship(
        "Instrument",
        secondary="instrument_external_publishing_bots",
        back_populates="external_publishing_bots",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Instruments to restrict the photometry to when publishing.",
    )

    streams = relationship(
        "Stream",
        secondary="stream_external_publishing_bots",
        back_populates="external_publishing_bots",
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

    enable_publish_to_hermes = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="Whether to enable publishing to Hermes or not.",
    )

    enable_publish_to_tns = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="Whether to enable publishing to TNS or not.",
    )
    # Fields specific to TNS
    bot_id = sa.Column(sa.Integer, doc="ID of the bot.", nullable=True)
    source_group_id = sa.Column(
        sa.Integer, doc="Source group ID of the bot.", nullable=True
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
        "ExternalPublishingBotGroup",
        back_populates="external_publishing_bot",
        passive_deletes=True,
        doc="Groups associated with this publishing bot.",
    )

    coauthors = relationship(
        "ExternalPublishingBotCoauthor",
        back_populates="external_publishing_bot",
        passive_deletes=True,
        doc="Coauthors associated with this publishing bot.",
    )


# we want a unique constraint on the bot_name, bot_id, source_group_id, testing columns
# this way you can't have the same bot twice, except for testing
ExternalPublishingBot.__table_args__ = (
    sa.UniqueConstraint("bot_name", "bot_id", "source_group_id", "testing"),
)


class ExternalPublishingBotCoauthor(Base):
    """Coauthors for external publishing bots."""

    __tablename__ = "external_publishing_bot_coauthors"

    external_publishing_bot_id = sa.Column(
        sa.ForeignKey("external_publishing_bots.id", ondelete="CASCADE"), nullable=False
    )
    user_id = sa.Column(sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    external_publishing_bot = relationship(
        "ExternalPublishingBot",
        back_populates="coauthors",
        doc="The ExternalPublishingBot associated with this mapper.",
    )


# unique constraint on the external_publishing_bot_id and user_id columns
ExternalPublishingBotCoauthor.__table_args__ = (
    sa.UniqueConstraint("external_publishing_bot_id", "user_id"),
)


class ExternalPublishingBotGroup(Base):
    """Mapper between ExternalPublishingBots and Groups."""

    __tablename__ = "external_publishing_bot_groups"

    external_publishing_bot_id = sa.Column(
        sa.ForeignKey("external_publishing_bots.id", ondelete="CASCADE"), nullable=False
    )
    group_id = sa.Column(sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)

    owner = sa.Column(sa.Boolean, nullable=False, default=False)
    auto_publish_to_tns = sa.Column(sa.Boolean, nullable=False, server_default="false")
    auto_publish_to_hermes = sa.Column(
        sa.Boolean, nullable=False, server_default="false"
    )
    auto_publish_allow_bots = sa.Column(
        sa.Boolean, nullable=False, server_default="false"
    )

    external_publishing_bot = relationship(
        "ExternalPublishingBot",
        back_populates="groups",
        doc="The ExternalPublishingBot associated with this mapper.",
    )

    group = relationship(
        "Group",
        back_populates="external_publishing_bots",
        doc="The Group associated with this mapper.",
    )

    auto_publishers = relationship(
        "ExternalPublishingBotGroupAutoPublisher",
        back_populates="external_publishing_bot_group",
        passive_deletes=True,
        doc="Users associated with this ExternalPublishingBotGroup.",
    )


# we want a unique index on the external_publishing_bot_id and group_id columns
ExternalPublishingBotGroup.__table_args__ = (
    sa.UniqueConstraint("external_publishing_bot_id", "group_id"),
)


class ExternalPublishingBotGroupAutoPublisher(Base):
    """Mapper between ExternalPublishingBots and Users that are allowed to auto-publish."""

    __tablename__ = "external_publishing_bot_group_users"

    external_publishing_bot_group_id = sa.Column(
        sa.ForeignKey("external_publishing_bot_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_user_id = sa.Column(
        sa.ForeignKey("group_users.id", ondelete="CASCADE"), nullable=False
    )

    external_publishing_bot_group = relationship(
        "ExternalPublishingBotGroup",
        back_populates="auto_publishers",
        doc="The ExternalPublishingBot associated with this mapper.",
    )


# we want a unique index on the external_publishing_bot_id and group_user_id columns
ExternalPublishingBotGroupAutoPublisher.__table_args__ = (
    sa.UniqueConstraint("external_publishing_bot_group_id", "group_user_id"),
)

# we add a method that gives us the user_id from that group_user
ExternalPublishingBotGroupAutoPublisher.user_id = column_property(
    sa.select(GroupUser.user_id)
    .where(GroupUser.id == ExternalPublishingBotGroupAutoPublisher.group_user_id)
    .scalar_subquery()
)


class ExternalPublishingSubmission(Base):
    """Objects to be auto-submitted."""

    __tablename__ = "external_publishing_submissions"

    external_publishing_bot_id = sa.Column(
        sa.ForeignKey("external_publishing_bots.id", ondelete="CASCADE"), nullable=False
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
        default=False,
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
        default=False,
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

    external_publishing_bot = relationship(
        "ExternalPublishingBot",
        back_populates="submissions",
        doc="The ExternalPublishingBot associated with this mapper.",
    )

    obj = relationship(
        "Obj",
        back_populates="external_publishing_submissions",
        doc="The Obj associated with this mapper.",
    )

    user = relationship(
        "User",
        back_populates="external_publishing_submissions",
        doc="The User associated with this mapper.",
    )


ExternalPublishingBot.submissions = relationship(
    "ExternalPublishingSubmission",
    back_populates="external_publishing_bot",
    passive_deletes=True,
    doc="Auto-submissions associated with this ExternalPublishingBot.",
)


def external_publishing_bot_read_access_logic(cls, user_or_token):
    """Return a query that filters ExternalPublishingBot instances based on user read access."""
    # if the user is a system admin, they can see all ExternalPublishingBots
    # otherwise, they can only see ExternalPublishingBots that are associated with groups they are in
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.join(ExternalPublishingBotGroup)
        query = query.where(
            ExternalPublishingBotGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            )
        )
    return query


def external_publishing_bot_update_delete_access_logic(cls, user_or_token):
    """Return a query that filters ExternalPublishingBot instances based on user update/delete access."""
    # same as read access, but at least one of the groups must be an owner of the ExternalPublishingBot
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.join(ExternalPublishingBotGroup)
        query = query.where(
            ExternalPublishingBotGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            ),
            ExternalPublishingBotGroup.owner.is_(True),
        )
    return query


ExternalPublishingBot.read = CustomUserAccessControl(
    external_publishing_bot_read_access_logic
)
ExternalPublishingBot.update = ExternalPublishingBot.delete = CustomUserAccessControl(
    external_publishing_bot_update_delete_access_logic
)


def external_publishing_bot_coauthor_read_access_logic(cls, user_or_token):
    """Return a query that filters ExternalPublishingBotCoauthor instances based on user read access."""
    # if the user is a system admin, they can see all ExternalPublishingBotCoauthors
    # otherwise, they can only see ExternalPublishingBotCoauthors from ExternalPublishingBots that are associated with groups they are in
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.where(
            ExternalPublishingBotCoauthor.external_publishing_bot_id.in_(
                sa.select(ExternalPublishingBotGroup.external_publishing_bot_id).where(
                    ExternalPublishingBotGroup.group_id.in_(
                        sa.select(GroupUser.group_id).where(
                            GroupUser.user_id == user_id
                        )
                    ),
                )
            ),
        )
    return query


def external_publishing_bot_coauthor_create_update_delete_access_logic(
    cls, user_or_token
):
    """Return a query that filters ExternalPublishingBotCoauthor instances based on user create/update/delete access."""
    # same as read access, but at least one of the groups must be an owner of the ExternalPublishingBot
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.where(
            ExternalPublishingBotCoauthor.external_publishing_bot_id.in_(
                sa.select(ExternalPublishingBotGroup.external_publishing_bot_id).where(
                    ExternalPublishingBotGroup.group_id.in_(
                        sa.select(GroupUser.group_id).where(
                            GroupUser.user_id == user_id
                        )
                    ),
                    ExternalPublishingBotGroup.owner.is_(True),
                )
            ),
        )
    return query


ExternalPublishingBotCoauthor.read = CustomUserAccessControl(
    external_publishing_bot_coauthor_read_access_logic
)

ExternalPublishingBotCoauthor.create = ExternalPublishingBotCoauthor.update = (
    ExternalPublishingBotCoauthor.delete
) = CustomUserAccessControl(
    external_publishing_bot_coauthor_create_update_delete_access_logic
)


def external_publishing_bot_group_read_access_logic(cls, user_or_token):
    """Return a query that filters ExternalPublishingBotGroup instances based on user read access."""
    # if the user is a system admin, they can see all ExternalPublishingBotGroups
    # otherwise, they can only see ExternalPublishingBotGroups that are associated with groups they are in
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        # a user should only be able to read ExternalPublishingBotGroups that are associated with groups
        # to which they have access
        query = query.where(
            ExternalPublishingBotGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            )
        )
    return query


def external_publishing_bot_group_create_update_delete_access_logic(cls, user_or_token):
    """Return a query that filters ExternalPublishingBotGroup instances based on user create/update/delete access."""
    # same as read access, but at least one of the groups must be an owner of the ExternalPublishingBot
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        # 1. the user has access to the group
        # 2. the user has access to any group that is associated with the bot as an owner
        query = query.where(
            ExternalPublishingBotGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            ),
            ExternalPublishingBotGroup.external_publishing_bot_id.in_(
                sa.select(ExternalPublishingBotGroup.external_publishing_bot_id).where(
                    ExternalPublishingBotGroup.group_id.in_(
                        sa.select(GroupUser.group_id).where(
                            GroupUser.user_id == user_id
                        )
                    ),
                    ExternalPublishingBotGroup.owner.is_(True),
                )
            ),
        )
    return query


ExternalPublishingBotGroup.read = CustomUserAccessControl(
    external_publishing_bot_group_read_access_logic
)
ExternalPublishingBotGroup.create = ExternalPublishingBotGroup.update = (
    ExternalPublishingBotGroup.delete
) = CustomUserAccessControl(
    external_publishing_bot_group_create_update_delete_access_logic
)

# for the ExternalPublishingBotGroupAutoPublisher, we will use the same access logic as for ExternalPublishingBotGroup
ExternalPublishingBotGroupAutoPublisher.read = CustomUserAccessControl(
    external_publishing_bot_read_access_logic
)
ExternalPublishingBotGroupAutoPublisher.create = (
    ExternalPublishingBotGroupAutoPublisher.update
) = ExternalPublishingBotGroupAutoPublisher.delete = CustomUserAccessControl(
    external_publishing_bot_update_delete_access_logic
)


def external_publishing_submission_access_logic(cls, user_or_token):
    """Return a query that filters ExternalPublishingSubmission instances based on user read/create/update/delete access."""
    # if the user is a system admin, they can create/read/update/delete all ExternalPublishingSubmissions
    # otherwise, they can do so only using ExternalPublishingBots that are associated with groups they are in
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.where(
            ExternalPublishingSubmission.external_publishing_bot_id.in_(
                sa.select(ExternalPublishingBot.id)
                .join(ExternalPublishingBotGroup)
                .join(Group)
                .join(GroupUser)
                .where(GroupUser.user_id == user_id)
            )
        )
    return query


ExternalPublishingSubmission.read = ExternalPublishingSubmission.create = (
    ExternalPublishingSubmission.update
) = ExternalPublishingSubmission.delete = CustomUserAccessControl(
    external_publishing_submission_access_logic
)
