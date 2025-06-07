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
                            auto_publish:
                                type: boolean
                                description: Whether to automatically publish to this group
                            auto_publish_allow_bots:
                                type: boolean
                                description: Whether to allow bots to automatically publish to this group
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

        # process the boolean values
        for field in ["auto_publish", "auto_publish_allow_bots", "owner"]:
            if field in data:
                data[field] = str_to_bool(data[field])
        auto_publish = data.get("auto_publish")
        auto_publish_allow_bots = data.get("auto_publish_allow_bots")
        owner = data.get("owner")

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

            # check if the group already has access to the external_publishing_bot
            external_publishing_bot_group = session.scalar(
                ExternalPublishingBotGroup.select(session.user_or_token).where(
                    ExternalPublishingBotGroup.external_publishing_bot_id
                    == external_publishing_bot_id,
                    ExternalPublishingBotGroup.group_id == group_id,
                )
            )

            if external_publishing_bot_group:
                if (
                    auto_publish is None
                    and owner is None
                    and auto_publish_allow_bots is None
                ):
                    return self.error(
                        "You must specify auto_publish, owner and/or auto_publish_allow_bots when editing a publishing bot group"
                    )

                if (
                    auto_publish is not None
                    and auto_publish != external_publishing_bot_group.auto_publish
                ):
                    external_publishing_bot_group.auto_publish = auto_publish
                if (
                    auto_publish_allow_bots is not None
                    and auto_publish_allow_bots
                    != external_publishing_bot_group.auto_publish_allow_bots
                ):
                    # if the user is trying to set auto_report_allow_bots to False,
                    # we need to verify that none of the existing auto publishers are bots
                    if auto_publish_allow_bots is False:
                        auto_publishers_group_users = session.scalars(
                            sa.select(GroupUser).where(
                                GroupUser.id.in_(
                                    [
                                        r.group_user_id
                                        for r in external_publishing_bot_group.auto_publishers
                                    ]
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
                    external_publishing_bot_group.auto_publish_allow_bots = (
                        auto_publish_allow_bots
                    )

                if owner is not None and owner != external_publishing_bot_group.owner:
                    # Check if this is the only owner group
                    owners = [
                        group.group_id
                        for group in external_publishing_bot_group.external_publishing_bot.groups
                        if group.owner
                    ]

                    if owners == [group_id]:
                        return self.error(
                            "Cannot remove ownership from the only group owning this bot. Please assign another group as owner first."
                        )

                    external_publishing_bot_group.owner = owner

                session.commit()
                self.push(
                    action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
                )
                return self.success(data=external_publishing_bot_group)
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

                external_publishing_bot_group = ExternalPublishingBotGroup(
                    external_publishing_bot_id=external_publishing_bot_id,
                    group_id=group_id,
                    auto_publish=auto_publish,
                    auto_publish_allow_bots=auto_publish_allow_bots,
                    owner=owner,
                )

                session.add(external_publishing_bot_group)
                session.commit()
                self.push(
                    action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
                )
                return self.success(data={"id": external_publishing_bot_group.id})

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
