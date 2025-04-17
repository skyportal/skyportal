from baselayer.app.access import permissions
from baselayer.log import make_log

from ....models import (
    GroupUser,
    TNSRobot,
    TNSRobotGroup,
    TNSRobotGroupAutoreporter,
    User,
)
from ...base import BaseHandler

log = make_log("api/tns_robot_group_autoreporter")


class TNSRobotGroupAutoreporterHandler(BaseHandler):
    @permissions(["Manage TNS robots"])
    def post(self, tnsrobot_id, group_id, user_id=None):
        """
        ---
        summary: Add autoreporter(s) to a TNSRobotGroup
        description: Add autoreporter(s) to a TNSRobotGroup
        tags:
            - tns robot
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: string
              description: The ID of the TNSRobot
            - in: path
              name: group_id
              required: true
              schema:
                type: string
              description: The ID of the group to add autoreporter(s) to
            - in: query
              name: user_id
              required: false
              schema:
                type: string
              description: The ID of the user to add as an autoreporter
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
                                    An array of user IDs to add as autoreporters.
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

        if user_id is None:
            user_id = self.get_json().get("user_id", None)

        user_ids = [user_id]

        if "user_ids" in self.get_json():
            user_ids = self.get_json()["user_ids"]
            if isinstance(user_ids, str | int):
                user_ids = [int(user_id) for user_id in str(user_ids).split(",")]
            elif isinstance(user_ids, list):
                user_ids = [int(user_id) for user_id in user_ids]

        if len(user_ids) == 0:
            return self.error(
                "You must specify at least one user_id when adding autoreporter(s) for a TNSRobotGroup"
            )

        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(f"No TNSRobot with ID {tnsrobot_id}, or unaccessible")

            # verify that the user has access to the group
            if not self.current_user.is_system_admin and group_id not in [
                g.id for g in self.current_user.accessible_groups
            ]:
                return self.error(
                    f"Group {group_id} is not accessible by the current user"
                )

            # check if the group already has access to the tnsrobot
            tnsrobot_group = session.scalar(
                TNSRobotGroup.select(session.user_or_token).where(
                    TNSRobotGroup.tnsrobot_id == tnsrobot_id,
                    TNSRobotGroup.group_id == group_id,
                )
            )

            if tnsrobot_group is None:
                return self.error(
                    f"Group {group_id} does not have access to TNSRobot {tnsrobot_id}, cannot add autoreporter"
                )

            autoreporters = []
            for user_id in user_ids:
                # verify that the user has access to the user_id
                user = session.scalar(
                    User.select(session.user_or_token).where(User.id == user_id)
                )
                if user is None:
                    return self.error(f"No user with ID {user_id}, or unaccessible")

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

                # verify that the user isn't already an autoreporter
                existing_autoreporter = session.scalar(
                    TNSRobotGroupAutoreporter.select(session.user_or_token).where(
                        TNSRobotGroupAutoreporter.tnsrobot_group_id
                        == tnsrobot_group.id,
                        TNSRobotGroupAutoreporter.group_user_id == group_user.id,
                    )
                )

                if existing_autoreporter is not None:
                    return self.error(
                        f"User {user_id} is already an autoreporter for TNSRobot {tnsrobot_id}"
                    )

                # if the user has no affiliations, return an error (autoreporting would not work)
                if len(user.affiliations) == 0:
                    return self.error(
                        f"User {user_id} has no affiliation(s), required to be an autoreporter of TNSRobot {tnsrobot_id}. User must add one in their profile."
                    )

                # if the user is a bot user and the tnsrobot_group did not allow bot users, return an error
                if user.is_bot and not tnsrobot_group.auto_report_allow_bots:
                    return self.error(
                        f"User {user_id} is a bot user, which is not allowed to be an autoreporter for TNSRobot {tnsrobot_id}"
                    )

                autoreporter = TNSRobotGroupAutoreporter(
                    tnsrobot_group_id=tnsrobot_group.id, group_user_id=group_user.id
                )
                autoreporters.append(autoreporter)

            for a in autoreporters:
                session.add(a)
            session.commit()
            self.push(
                action="skyportal/REFRESH_TNSROBOTS",
            )
            return self.success(data={"ids": [a.id for a in autoreporters]})

    @permissions(["Manage TNS robots"])
    def delete(self, tnsrobot_id, group_id, user_id):
        """
        ---
        summary: Remove autoreporter(s) from a TNSRobotGroup
        description: Delete an autoreporter from a TNSRobotGroup
        tags:
            - tns robot
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: integer
              description: The ID of the TNSRobot
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
              description: The ID of the User to remove as an autoreporter. If not provided, the user_id will be taken from the request body.
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            user_id:
                                type: integer
                                description: The ID of the User to remove as an autoreporter
                            user_ids:
                                type: array
                                items:
                                    type: integer
                                description: The IDs of the Users to remove as autoreporters, overrides user_id
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

        if user_id is None:
            user_id = self.get_json().get("user_id", None)

        user_ids = [user_id]

        if "user_ids" in self.get_json():
            user_ids = self.get_json()["user_ids"]
            if isinstance(user_ids, str | int):
                user_ids = [int(user_id) for user_id in str(user_ids).split(",")]
            elif isinstance(user_ids, list):
                user_ids = [int(user_id) for user_id in user_ids]

        if len(user_ids) == 0:
            return self.error(
                "You must specify at least one user_id when removing autoreporter(s) from a TNSRobotGroup"
            )

        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(f"No TNSRobot with ID {tnsrobot_id}, or unaccessible")

            # verify that the user has access to the group
            if not self.current_user.is_system_admin and group_id not in [
                g.id for g in self.current_user.accessible_groups
            ]:
                return self.error(
                    f"Group {group_id} is not accessible by the current user"
                )

            # check if the group already has access to the tnsrobot
            tnsrobot_group = session.scalar(
                TNSRobotGroup.select(session.user_or_token).where(
                    TNSRobotGroup.tnsrobot_id == tnsrobot_id,
                    TNSRobotGroup.group_id == group_id,
                )
            )

            if tnsrobot_group is None:
                return self.error(
                    f"Group {group_id} does not have access to TNSRobot {tnsrobot_id}, cannot remove autoreporter"
                )

            autoreporters = []
            for user_id in user_ids:
                # verify that the user has access to the user_id
                user = session.scalar(
                    User.select(session.user_or_token).where(User.id == user_id)
                )
                if user is None:
                    return self.error(f"No user with ID {user_id}, or unaccessible")

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

                # verify that the user is an autoreporter
                autoreporter = session.scalar(
                    TNSRobotGroupAutoreporter.select(session.user_or_token).where(
                        TNSRobotGroupAutoreporter.tnsrobot_group_id
                        == tnsrobot_group.id,
                        TNSRobotGroupAutoreporter.group_user_id == group_user.id,
                    )
                )

                if autoreporter is None:
                    return self.error(
                        f"User {user_id} is not an autoreporter for TNSRobot {tnsrobot_id}"
                    )

                autoreporters.append(autoreporter)

            for a in autoreporters:
                session.delete(a)

            session.commit()
            self.push(
                action="skyportal/REFRESH_TNSROBOTS",
            )
            return self.success()
