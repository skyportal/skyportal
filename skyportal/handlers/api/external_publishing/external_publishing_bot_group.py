import sqlalchemy as sa

from baselayer.app.access import permissions
from baselayer.log import make_log

from ....models import (
    ExternalPublishingBotGroup,
    GroupUser,
)
from ....utils.data_access import check_access_to_external_publishing_bot
from ....utils.parse import str_to_bool
from ...base import BaseHandler

log = make_log("api/external_publishing_bot_group")


class ExternalPublishingBotGroupHandler(BaseHandler):
    @permissions(["Manage external publishing bots"])
    def put(self, external_publishing_bot_id, group_id=None):
        """
        ---
        summary: Add or edit a group for an external publishing bot
        description: Add or edit a group for an external publishing bot
        tags:
            - external publishing bot
        parameters:
            - in: path
              name: external_publishing_bot_id
              required: true
              schema:
                type: integer
              description: ID of the external publishing bot
            - in: path
              name: group_id
              required: false
              schema:
                type: integer
              description: ID of the group to edit
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            group_id:
                                type: integer
                                description: ID of the group to add
                            auto_publish_to_tns:
                                type: boolean
                                description: Whether to automatically publish to TNS
                            auto_publish_to_hermes:
                                type: boolean
                                description: Whether to automatically publish to Hermes
                            auto_publish_allow_bots:
                                type: boolean
                                description: Whether to allow bots to automatically publish
                            owner:
                                type: boolean
                                description: Whether this group is the owner of the external publishing bot
        responses:
            200:
                content:
                    application/json:
                        schema: Success
            400:
                content:
                    application/json:
                        schema: Error
        """
        data = self.get_json()
        auto_publish_to_tns = (
            str_to_bool(data.get("auto_publish_to_tns"))
            if "auto_publish_to_tns" in data
            else None
        )
        auto_publish_to_hermes = (
            str_to_bool(data.get("auto_publish_to_hermes"))
            if "auto_publish_to_hermes" in data
            else None
        )
        auto_publish_allow_bots = (
            str_to_bool(data.get("auto_publish_allow_bots"))
            if "auto_publish_allow_bots" in data
            else None
        )
        owner = str_to_bool(data.get("owner")) if "owner" in data else None

        group_id = data.get("group_id", group_id)
        if group_id is None:
            return self.error(
                "You must specify a group_id when giving or editing the access to a publishing bot for a group"
            )
        try:
            group_id = int(group_id)
        except ValueError:
            return self.error(f"Invalid group_id: {group_id}, must be an integer")

        with self.Session() as session:
            # Check if the user has access to the external_publishing_bot and group
            check_access_to_external_publishing_bot(
                session, session.user_or_token, external_publishing_bot_id
            )
            self.current_user.assert_group_accessible(group_id)

            # check if a bot group already exist
            bot_group = session.scalar(
                ExternalPublishingBotGroup.select(session.user_or_token).where(
                    ExternalPublishingBotGroup.external_publishing_bot_id
                    == external_publishing_bot_id,
                    ExternalPublishingBotGroup.group_id == group_id,
                )
            )

            if bot_group:
                # If this is an edit, check if the user has selected at least one field to update
                if (
                    auto_publish_to_tns is None
                    and auto_publish_to_hermes is None
                    and auto_publish_allow_bots is None
                    and owner is None
                ):
                    return self.error(
                        "You must update at least one of: auto_publish_to_tns, auto_publish_to_hermes, owner, or auto_publish_allow_bots when editing a bot group."
                    )
                if (
                    auto_publish_to_tns is not None
                    and auto_publish_to_tns != bot_group.auto_publish_to_tns
                ):
                    bot_group.auto_publish_to_tns = auto_publish_to_tns
                if (
                    auto_publish_to_hermes is not None
                    and auto_publish_to_hermes != bot_group.auto_publish_to_hermes
                ):
                    bot_group.auto_publish_to_hermes = auto_publish_to_hermes
                if (
                    auto_publish_allow_bots is not None
                    and auto_publish_allow_bots != bot_group.auto_publish_allow_bots
                ):
                    # if the user is trying to set auto_report_allow_bots to False,
                    # we need to verify that none of the existing auto publishers are bots
                    if auto_publish_allow_bots is False:
                        auto_publishers_group_users = session.scalars(
                            sa.select(GroupUser).where(
                                GroupUser.id.in_(
                                    [r.group_user_id for r in bot_group.auto_publishers]
                                )
                            )
                        )
                        if any(
                            group_user.user.is_bot
                            for group_user in auto_publishers_group_users
                        ):
                            return self.error(
                                "Cannot set auto_publish_allow_bots to False when one or more auto_publishers are bots. Remove the bots from the auto_publishers first."
                            )
                    bot_group.auto_publish_allow_bots = auto_publish_allow_bots

                if owner is not None and owner != bot_group.owner:
                    # Check if this is the only owner group
                    owners = [
                        group.group_id
                        for group in bot_group.external_publishing_bot.groups
                        if group.owner
                    ]

                    if owners == [group_id]:
                        return self.error(
                            "Cannot remove ownership from the only group owning this bot. Please assign another group as owner first."
                        )

                    bot_group.owner = owner

                session.commit()
                self.push(
                    action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
                )
                return self.success(data=bot_group)
            else:
                # Check if the association already exists but is inaccessible to the current user
                existing_association = session.scalar(
                    sa.select(ExternalPublishingBotGroup).where(
                        ExternalPublishingBotGroup.external_publishing_bot_id
                        == external_publishing_bot_id,
                        ExternalPublishingBotGroup.group_id == group_id,
                    )
                )
                if existing_association is not None:
                    return self.error(
                        f"Group {group_id} already has access to publishing bot {external_publishing_bot_id}, but user is not allowed to edit it"
                    )

                bot_group = ExternalPublishingBotGroup(
                    external_publishing_bot_id=external_publishing_bot_id,
                    group_id=group_id,
                    auto_publish_to_tns=auto_publish_to_tns,
                    auto_publish_to_hermes=auto_publish_to_hermes,
                    auto_publish_allow_bots=auto_publish_allow_bots,
                    owner=owner,
                )

                session.add(bot_group)
                session.commit()
                self.push(
                    action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
                )
                return self.success(data={"id": bot_group.id})

    @permissions(["Manage external publishing bots"])
    def delete(self, external_publishing_bot_id, group_id):
        """
        ---
        summary: Delete a group from an external publishing bot
        description: Delete a group from an external publishing bot
        tags:
            - external publishing bot
        parameters:
            - in: path
              name: external_publishing_bot_id
              required: true
              schema:
                type: string
              description: The ID of the external publishing bot
            - in: path
              name: group_id
              required: true
              schema:
                type: string
              description: The ID of the group to remove from the external publishing bot
        responses:
            200:
                content:
                    application/json:
                        schema: Success
            400:
                content:
                    application/json:
                        schema: Error
        """
        if group_id is None:
            return self.error(
                "You must specify a group_id when giving or editing the access to a publishing bot for a group"
            )
        with self.Session() as session:
            # Check if the user has access to the external_publishing_bot and group
            check_access_to_external_publishing_bot(
                session, session.user_or_token, external_publishing_bot_id
            )
            self.current_user.assert_group_accessible(group_id)

            # check if the group already has access to the external_publishing_bot
            external_publishing_bot_group = session.scalar(
                ExternalPublishingBotGroup.select(
                    session.user_or_token, mode="delete"
                ).where(
                    ExternalPublishingBotGroup.external_publishing_bot_id
                    == external_publishing_bot_id,
                    ExternalPublishingBotGroup.group_id == group_id,
                )
            )

            if external_publishing_bot_group is None:
                return self.error(
                    f"Group {group_id} does not have access to publishing bot {external_publishing_bot_id}, or user is not allowed to remove it"
                )

            # Prevent removing the last owner group
            owners = [
                g
                for g in external_publishing_bot_group.external_publishing_bot.groups
                if g.owner
            ]

            if len(owners) == 1 and external_publishing_bot_group.owner:
                return self.error(
                    "Cannot delete the only group owning this bot, add another group as an owner first."
                )

            session.delete(external_publishing_bot_group)
            session.commit()
            self.push(
                action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
            )
            return self.success()
