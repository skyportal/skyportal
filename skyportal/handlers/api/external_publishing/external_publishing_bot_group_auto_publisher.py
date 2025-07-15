from baselayer.app.access import permissions
from baselayer.log import make_log

from ....models import (
    ExternalPublishingBotGroup,
    ExternalPublishingBotGroupAutoPublisher,
    GroupUser,
    User,
)
from ....utils.data_access import check_access_to_external_publishing_bot
from ....utils.parse import get_list_typed
from ...base import BaseHandler

log = make_log("api/external_publishing_bot_group_auto_publisher")


class ExternalPublishingBotGroupAutoPublisherHandler(BaseHandler):
    @permissions(["Manage external publishing bots"])
    def post(self, external_publishing_bot_id, group_id, user_id=None):
        """
        ---
        summary: Add auto_publisher(s) to an ExternalPublishingBotGroup
        description: Add auto_publisher(s) to an ExternalPublishingBotGroup
        tags:
            - external publishing bot
        parameters:
            - in: path
              name: external_publishing_bot_id
              required: true
              schema:
                type: string
              description: The ID of the ExternalPublishingBot
            - in: path
              name: group_id
              required: true
              schema:
                type: string
              description: The ID of the group to add auto_publisher(s) to
            - in: query
              name: user_id
              required: false
              schema:
                type: string
              description: The ID of the user to add as an auto_publisher
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            user_ids:
                                type: array
                                items:
                                    type: string
                                description: |
                                    An array of user IDs to add as auto_publishers.
                                    If a string is provided, it will be split by commas.
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

        user_ids = get_list_typed(data.get("user_ids", []), int)

        if not user_ids:
            user_id = data.get("user_id") if user_id is None else user_id
            if user_id is not None:
                user_ids = [int(user_id)]

        if not user_ids:
            return self.error(
                "You must specify at least one user_id when adding auto_publisher(s) for an ExternalPublishingBotGroup"
            )

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
            if not external_publishing_bot_group:
                return self.error(
                    f"Group {group_id} does not have access to the publishing bot {external_publishing_bot_id}, cannot add auto_publisher"
                )

            new_auto_publishers = []
            for user_id in user_ids:
                # verify that the user has access to the user_id
                user = session.scalar(
                    User.select(session.user_or_token).where(User.id == user_id)
                )
                if user is None:
                    return self.error(f"No user with ID {user_id}, or inaccessible")

                # verify that the user specified is a group user of the group
                group_user = session.scalar(
                    GroupUser.select(session.user_or_token).where(
                        GroupUser.group_id == group_id, GroupUser.user_id == user_id
                    )
                )
                if group_user is None:
                    return self.error(
                        f"User {user_id} is not a member of group {group_id}"
                    )

                # verify that the user isn't already an auto_publisher
                existing_auto_publisher = session.scalar(
                    ExternalPublishingBotGroupAutoPublisher.select(
                        session.user_or_token
                    ).where(
                        ExternalPublishingBotGroupAutoPublisher.external_publishing_bot_group_id
                        == external_publishing_bot_group.id,
                        ExternalPublishingBotGroupAutoPublisher.group_user_id
                        == group_user.id,
                    )
                )

                if existing_auto_publisher:
                    return self.error(
                        f"User {user_id} is already an auto_publisher for the publishing bot {external_publishing_bot_id}"
                    )

                if len(user.affiliations) == 0:
                    return self.error(
                        f"User {user_id} has no affiliation(s), required to be an auto_publisher of the publishing bot {external_publishing_bot_id}. User must add one in their profile."
                    )

                if (
                    user.is_bot
                    and not external_publishing_bot_group.auto_report_allow_bots
                ):
                    return self.error(
                        f"User {user_id} is a bot user, which is not allowed to be an auto_publisher for the publishing bot {external_publishing_bot_id}"
                    )

                new_auto_publishers.append(
                    ExternalPublishingBotGroupAutoPublisher(
                        external_publishing_bot_group_id=external_publishing_bot_group.id,
                        group_user_id=group_user.id,
                    )
                )

            session.add_all(new_auto_publishers)
            session.commit()
            self.push(
                action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
            )
            return self.success(data={"ids": [a.id for a in new_auto_publishers]})

    @permissions(["Manage external publishing bots"])
    def delete(self, external_publishing_bot_id, group_id, user_id):
        """
        ---
        summary: Remove auto_publisher(s) from an ExternalPublishingBotGroup
        description: Delete an auto_publisher from an ExternalPublishingBotGroup
        tags:
            - external publishing bot
        parameters:
            - in: path
              name: external_publishing_bot_id
              required: true
              schema:
                type: integer
              description: The ID of the external publishing bot
            - in: path
              name: group_id
              required: true
              schema:
                type: integer
              description: The ID of the Group
            - in: path
              name: user_id
              required: false
              schema:
                type: integer
              description: The ID of the User to remove as an auto_publisher. If not provided, the user_id will be taken from the request body.
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            user_id:
                                type: integer
                                description: The ID of the User to remove as an auto_publisher
                            user_ids:
                                type: array
                                items:
                                    type: integer
                                description: The IDs of the Users to remove as auto_publishers, overrides user_id
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

        user_ids = get_list_typed(data.get("user_ids", []), int)
        if not user_ids:
            user_id = data.get("user_id") if user_id is None else user_id
            if user_id is not None:
                user_ids = [int(user_id)]
        if not user_ids:
            return self.error(
                "You must specify at least one user_id when removing auto_publisher(s) from an ExternalPublishingBotGroup"
            )

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
            if external_publishing_bot_group is None:
                return self.error(
                    f"Group {group_id} does not have access to the publishing bot {external_publishing_bot_id}, cannot remove auto_publisher"
                )

            auto_publishers_to_delete = []
            for user_id in user_ids:
                # verify that the user has access to the user_id
                user = session.scalar(
                    User.select(session.user_or_token).where(User.id == user_id)
                )
                if user is None:
                    return self.error(f"No user with ID {user_id}, or inaccessible")

                # verify that the user specified is a group user of the group
                group_user = session.scalar(
                    GroupUser.select(session.user_or_token).where(
                        GroupUser.group_id == group_id, GroupUser.user_id == user_id
                    )
                )
                if group_user is None:
                    return self.error(
                        f"User {user_id} is not a member of group {group_id}"
                    )

                # verify that the user is an auto_publisher
                auto_publisher = session.scalar(
                    ExternalPublishingBotGroupAutoPublisher.select(
                        session.user_or_token
                    ).where(
                        ExternalPublishingBotGroupAutoPublisher.external_publishing_bot_group_id
                        == external_publishing_bot_group.id,
                        ExternalPublishingBotGroupAutoPublisher.group_user_id
                        == group_user.id,
                    )
                )

                if auto_publisher is None:
                    return self.error(
                        f"User {user_id} is not an auto_publisher for the publishing bot {external_publishing_bot_id}"
                    )

                auto_publishers_to_delete.append(auto_publisher)

            for a in auto_publishers_to_delete:
                session.delete(a)
            session.commit()
            self.push(
                action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
            )
            return self.success()
