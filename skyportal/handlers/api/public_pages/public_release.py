import operator  # noqa: F401

from baselayer.app.access import auth_or_token
from baselayer.log import make_log
from ...base import BaseHandler

from ....models import PublicRelease, PublicSourcePage

log = make_log('api/public_release')


class PublicReleaseHandler(BaseHandler):
    async def post(self):
        """
        ---
          description:
            Create a new public release
          tags:
            - public_release
          requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            name:
                                type: string
                            description:
                                type: string
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
        if data is None or data == {}:
            return self.error("No data provided")
        name = data.get("name")
        if name is None or name == "":
            return self.error("Name is required")

        with self.Session() as session:
            public_release = PublicRelease(
                name=name, description=data.get("description", "")
            )
            session.add(public_release)
            session.commit()
            return self.success(data=public_release)

    def get(self):
        """
        ---
          description:
            Retrieve all public releases
          tags:
            - public_release
          responses:
            200:
              content:
                application/json:
                    schema: Success
            400:
              content:
                application/json:
                  schema: Error
            404:
              content:
                application/json:
                  schema: Error
        """
        with self.Session() as session:
            public_releases = session.execute(
                PublicRelease.select(session.user_or_token, mode="read").order_by(
                    PublicRelease.name.asc()
                )
            ).all()
            return self.success(data=public_releases)

    @auth_or_token
    def delete(self, release_id):
        """
        ---
        description: Delete a public release
        tags:
          - public_release
        parameters:
          - in: path
            name: release_id
            required: true
            schema:
              type: integer
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

        if release_id is None:
            return self.error("Missing release_id")

        with self.Session() as session:
            public_release = session.scalars(
                PublicRelease.select(session.user_or_token, mode="delete").where(
                    PublicRelease.id == release_id
                )
            ).first()

            if public_release is None:
                return self.error("Release not found", status=404)

            public_source_pages = (
                session.execute(
                    PublicSourcePage.select(session.user_or_token, mode="update").where(
                        PublicSourcePage.release_ids.any(release_id)
                    )
                )
                .unique()
                .all()
            )

            for public_source_page in public_source_pages:
                public_source_page.release_ids.remove(release_id)
                session.add(public_source_page)

            session.delete(public_release)
            session.commit()
            return self.success()
