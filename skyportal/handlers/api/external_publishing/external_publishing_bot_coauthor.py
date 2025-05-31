from baselayer.app.access import permissions
from baselayer.log import make_log

from ....models import User
from ....models.external_publishing_bot import (
    ExternalPublishingBot,
    ExternalPublishingBotCoauthor,
)
from ...base import BaseHandler

log = make_log("api/external_publishing_bot_coauthor")


class ExternalPublishingBotCoauthorHandler(BaseHandler):
    @permissions(["Manage external publishing bots"])
    def post(self, external_publishing_bot_id, user_id=None):
        """
        ---
        summary: Add a coauthor to an external publishing bot
        description: Add a coauthor to an external publishing bot
        tags:
            - external publishing bot
        parameters:
            - in: path
              name: external_publishing_bot_id
              required: true
              schema:
                type: integer
              description: ID of the publishing bot
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
                "You must specify a coauthor_id when adding a coauthor to a publishing bot"
            )
        with self.Session() as session:
            # verify that the user has access to the external_publishing_bot
            external_publishing_bot = session.scalar(
                ExternalPublishingBot.select(session.user_or_token).where(
                    ExternalPublishingBot.id == external_publishing_bot_id
                )
            )
            if external_publishing_bot is None:
                return self.error(
                    f"No publishing bot with ID {external_publishing_bot_id}, or inaccessible"
                )

            # verify that the user has access to the coauthor
            user = session.scalar(
                User.select(session.user_or_token).where(User.id == user_id)
            )
            if user is None:
                return self.error(f"No User with ID {user_id}, or inaccessible")

            if user_id in [
                coauthor.user_id for coauthor in external_publishing_bot.coauthors
            ]:
                return self.error(
                    f"User {user_id} is already a coauthor of publishing bot {external_publishing_bot_id}"
                )

            if len(user.affiliations) == 0:
                return self.error(
                    f"User {user_id} has no affiliation(s), required to be a coauthor. User must add one in their profile."
                )

            if user.is_bot:
                return self.error(f"User {user_id} is a bot and cannot be a coauthor")

            # add the coauthor
            coauthor = ExternalPublishingBotCoauthor(
                external_publishing_bot_id=external_publishing_bot_id, user_id=user_id
            )
            session.add(coauthor)
            session.commit()
            self.push(
                action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
            )
            return self.success(data={"id": coauthor.id})

    @permissions(["Manage external publishing bots"])
    def delete(self, external_publishing_bot_id, user_id):
        """
        ---
        summary: Remove a coauthor from an external publishing bot
        description: Remove a coauthor from an external publishing bot
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

        with self.Session() as session:
            # verify that the user has access to the external_publishing_bot
            external_publishing_bot = session.scalar(
                ExternalPublishingBot.select(session.user_or_token).where(
                    ExternalPublishingBot.id == external_publishing_bot_id
                )
            )
            if external_publishing_bot is None:
                return self.error(
                    f"No publishing bot with ID {external_publishing_bot_id}, or inaccessible"
                )

            # verify that the coauthor exists and/or can be deleted
            coauthor = session.scalar(
                ExternalPublishingBotCoauthor.select(
                    session.user_or_token, mode="delete"
                ).where(
                    ExternalPublishingBotCoauthor.user_id == user_id,
                    ExternalPublishingBotCoauthor.external_publishing_bot_id
                    == external_publishing_bot_id,
                )
            )
            if coauthor is None:
                return self.error(
                    f"No coauthor with ID {user_id}, or unable to delete it"
                )

            session.delete(coauthor)
            session.commit()
            self.push(
                action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
            )
            return self.success()
