from baselayer.app.access import permissions
from baselayer.log import make_log

from ....models import (
    GroupUser,
    SharingServiceGroup,
    SharingServiceGroupAutoPublisher,
    User,
)
from ....utils.data_access import check_access_to_sharing_service
from ....utils.parse import get_list_typed
from ...base import BaseHandler

log = make_log("api/sharing_service_group_auto_publisher")


class SharingServiceGroupAutoPublisherHandler(BaseHandler):
    @permissions(["Manage sharing services"])
    def post(self, sharing_service_id, group_id, user_id=None):
        """
        ---
        summary: Add auto_publisher(s) to an SharingServiceGroup
        description: Add auto_publisher(s) to an SharingServiceGroup
        tags:
            - external sharing service
        parameters:
            - in: path
              name: sharing_service_id
              required: true
              schema:
                type: string
              description: The ID of the SharingService
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
                "You must specify at least one user_id when adding auto_publisher(s) for an SharingServiceGroup"
            )

        with self.Session() as session:
            # Check if the user has access to the sharing_service and group
            check_access_to_sharing_service(
                session, session.user_or_token, sharing_service_id
            )
            self.current_user.assert_group_accessible(group_id)

            # check if the group already has access to the sharing_service
            sharing_service_group = session.scalar(
                SharingServiceGroup.select(session.user_or_token).where(
                    SharingServiceGroup.sharing_service_id == sharing_service_id,
                    SharingServiceGroup.group_id == group_id,
                )
            )
            if not sharing_service_group:
                return self.error(
                    f"Group {group_id} does not have access to the sharing service {sharing_service_id}, cannot add auto_publisher"
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
                    SharingServiceGroupAutoPublisher.select(
                        session.user_or_token
                    ).where(
                        SharingServiceGroupAutoPublisher.sharing_service_group_id
                        == sharing_service_group.id,
                        SharingServiceGroupAutoPublisher.group_user_id == group_user.id,
                    )
                )

                if existing_auto_publisher:
                    return self.error(
                        f"User {user_id} is already an auto_publisher for the sharing service {sharing_service_id}"
                    )

                if len(user.affiliations) == 0:
                    return self.error(
                        f"User {user_id} has no affiliation(s), required to be an auto_publisher of the sharing service {sharing_service_id}. User must add one in their profile."
                    )

                if user.is_bot and not sharing_service_group.auto_sharing_allow_bots:
                    return self.error(
                        f"User {user_id} is a bot user, which is not allowed to be an auto_publisher for the sharing service {sharing_service_id}"
                    )

                new_auto_publishers.append(
                    SharingServiceGroupAutoPublisher(
                        sharing_service_group_id=sharing_service_group.id,
                        group_user_id=group_user.id,
                    )
                )

            session.add_all(new_auto_publishers)
            session.commit()
            self.push(
                action="skyportal/REFRESH_SHARING_SERVICES",
            )
            return self.success(data={"ids": [a.id for a in new_auto_publishers]})

    @permissions(["Manage sharing services"])
    def delete(self, sharing_service_id, group_id, user_id):
        """
        ---
        summary: Remove auto_publisher(s) from an SharingServiceGroup
        description: Delete an auto_publisher from an SharingServiceGroup
        tags:
            - external sharing service
        parameters:
            - in: path
              name: sharing_service_id
              required: true
              schema:
                type: integer
              description: The ID of the external sharing service
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
                "You must specify at least one user_id when removing auto_publisher(s) from an SharingServiceGroup"
            )

        with self.Session() as session:
            # Check if the user has access to the sharing_service and group
            check_access_to_sharing_service(
                session, session.user_or_token, sharing_service_id
            )
            self.current_user.assert_group_accessible(group_id)

            # check if the group already has access to the sharing_service
            sharing_service_group = session.scalar(
                SharingServiceGroup.select(session.user_or_token).where(
                    SharingServiceGroup.sharing_service_id == sharing_service_id,
                    SharingServiceGroup.group_id == group_id,
                )
            )
            if sharing_service_group is None:
                return self.error(
                    f"Group {group_id} does not have access to the sharing service {sharing_service_id}, cannot remove auto_publisher"
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
                    SharingServiceGroupAutoPublisher.select(
                        session.user_or_token
                    ).where(
                        SharingServiceGroupAutoPublisher.sharing_service_group_id
                        == sharing_service_group.id,
                        SharingServiceGroupAutoPublisher.group_user_id == group_user.id,
                    )
                )

                if auto_publisher is None:
                    return self.error(
                        f"User {user_id} is not an auto_publisher for the sharing service {sharing_service_id}"
                    )

                auto_publishers_to_delete.append(auto_publisher)

            for a in auto_publishers_to_delete:
                session.delete(a)
            session.commit()
            self.push(
                action="skyportal/REFRESH_SHARING_SERVICES",
            )
            return self.success()
