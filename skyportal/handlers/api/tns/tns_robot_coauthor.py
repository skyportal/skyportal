from handlers.base import BaseHandler
from models import (
    TNSRobot,
    TNSRobotCoauthor,
    User,
)

from baselayer.app.access import permissions
from log import make_log

log = make_log("api/tns_robot_coauthor")


class TNSRobotCoauthorHandler(BaseHandler):
    @permissions(["Manage TNS robots"])
    def post(self, tnsrobot_id, user_id=None):
        """
        ---
        summary: Add a coauthor to a TNS robot
        description: Add a coauthor to a TNS robot
        tags:
            - tns robot
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: integer
              description: ID of the TNS robot
            - in: path
              name: user_id
              required: false
              schema:
                type: integer
              description: ID of the user to add as a coauthor
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            user_id:
                                type: integer
                                description: ID of the user to add as a coauthor, if not specified in the URL
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
            user_id = self.get_json().get("user_id")
        if user_id is None:
            return self.error(
                "You must specify a coauthor_id when adding a coauthor to a TNSRobot"
            )
        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(f"No TNSRobot with ID {tnsrobot_id}")

            # verify that the user has access to the coauthor
            user = session.scalar(
                User.select(session.user_or_token).where(User.id == user_id)
            )
            if user is None:
                return self.error(f"No User with ID {user_id}")

            # if the coauthor already exists, return an error
            if user_id in [u.user_id for u in tnsrobot.coauthors]:
                return self.error(
                    f"User {user_id} is already a coauthor of TNSRobot {tnsrobot_id}"
                )

            # if the user has no affiliations, return an error (autoreporting would not work)
            if len(user.affiliations) == 0:
                return self.error(
                    f"User {user_id} has no affiliation(s), required to be a coauthor of TNSRobot {tnsrobot_id}. User must add one in their profile."
                )

            # if the user is a bot, throw an error
            if user.is_bot:
                return self.error(
                    f"User {user_id} is a bot and cannot be a coauthor of TNSRobot {tnsrobot_id}"
                )

            # add the coauthor
            coauthor = TNSRobotCoauthor(tnsrobot_id=tnsrobot_id, user_id=user_id)
            session.add(coauthor)
            session.commit()
            self.push(
                action="skyportal/REFRESH_TNSROBOTS",
            )
            return self.success(data={"id": coauthor.id})

    @permissions(["Manage TNS robots"])
    def delete(self, tnsrobot_id, user_id):
        """
        ---
        summary: Remove a coauthor from a TNS robot
        description: Remove a coauthor from a TNS robot
        tags:
            - tns robot
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: integer
              description: ID of the TNS robot
            - in: path
              name: user_id
              required: true
              schema:
                type: integer
              description: ID of the user to remove as a coauthor
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

        # the DELETE handler is used to remove a coauthor from a TNSRobot
        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(f"No TNSRobot with ID {tnsrobot_id}, or unaccessible")

            # verify that the coauthor exists and/or can be deleted
            coauthor = session.scalar(
                TNSRobotCoauthor.select(session.user_or_token, mode="delete").where(
                    TNSRobotCoauthor.user_id == user_id,
                    TNSRobotCoauthor.tnsrobot_id == tnsrobot_id,
                )
            )
            if coauthor is None:
                return self.error(
                    f"No TNSRobotCoauthor with userID {user_id}, or unable to delete it"
                )

            session.delete(coauthor)
            session.commit()
            self.push(
                action="skyportal/REFRESH_TNSROBOTS",
            )
            return self.success()
