from baselayer.app.access import permissions
from baselayer.log import make_log

from ....models import SharingService, SharingServiceCoauthor, User
from ...base import BaseHandler

log = make_log("api/sharing_service_coauthor")


class SharingServiceCoauthorHandler(BaseHandler):
    @permissions(["Manage sharing services"])
    def post(self, sharing_service_id, user_id=None):
        """
        ---
        summary: Add a coauthor to an external sharing service
        description: Add a coauthor to an external sharing service
        tags:
            - external sharing service
        parameters:
            - in: path
              name: sharing_service_id
              required: true
              schema:
                type: integer
              description: ID of the sharing service
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
                "You must specify a coauthor_id when adding a coauthor to a sharing service"
            )
        with self.Session() as session:
            # verify that the user has access to the sharing_service
            sharing_service = session.scalar(
                SharingService.select(session.user_or_token).where(
                    SharingService.id == sharing_service_id
                )
            )
            if sharing_service is None:
                return self.error(
                    f"No sharing service with ID {sharing_service_id}, or inaccessible"
                )

            # verify that the user has access to the coauthor
            user = session.scalar(
                User.select(session.user_or_token).where(User.id == user_id)
            )
            if user is None:
                return self.error(f"No User with ID {user_id}, or inaccessible")

            if user_id in [coauthor.user_id for coauthor in sharing_service.coauthors]:
                return self.error(
                    f"User {user_id} is already a coauthor of sharing service {sharing_service_id}"
                )

            if len(user.affiliations) == 0:
                return self.error(
                    f"User {user_id} has no affiliation(s), required to be a coauthor. User must add one in their profile."
                )

            if user.is_bot:
                return self.error(f"User {user_id} is a bot and cannot be a coauthor")

            # add the coauthor
            coauthor = SharingServiceCoauthor(
                sharing_service_id=sharing_service_id, user_id=user_id
            )
            session.add(coauthor)
            session.commit()
            self.push(
                action="skyportal/REFRESH_SHARING_SERVICES",
            )
            return self.success(data={"id": coauthor.id})

    @permissions(["Manage sharing services"])
    def delete(self, sharing_service_id, user_id):
        """
        ---
        summary: Remove a coauthor from an external sharing service
        description: Remove a coauthor from an external sharing service
        tags:
            - external sharing service
        parameters:
            - in: path
              name: sharing_service_id
              required: true
              schema:
                type: integer
              description: ID of the external sharing service
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
            # verify that the user has access to the sharing_service
            sharing_service = session.scalar(
                SharingService.select(session.user_or_token).where(
                    SharingService.id == sharing_service_id
                )
            )
            if sharing_service is None:
                return self.error(
                    f"No sharing service with ID {sharing_service_id}, or inaccessible"
                )

            # verify that the coauthor exists and/or can be deleted
            coauthor = session.scalar(
                SharingServiceCoauthor.select(
                    session.user_or_token, mode="delete"
                ).where(
                    SharingServiceCoauthor.user_id == user_id,
                    SharingServiceCoauthor.sharing_service_id == sharing_service_id,
                )
            )
            if coauthor is None:
                return self.error(
                    f"No coauthor with ID {user_id}, or unable to delete it"
                )

            session.delete(coauthor)
            session.commit()
            self.push(
                action="skyportal/REFRESH_SHARING_SERVICES",
            )
            return self.success()
