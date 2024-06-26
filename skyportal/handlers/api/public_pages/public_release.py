import operator  # noqa: F401
import re

from baselayer.app.access import auth_or_token
from baselayer.log import make_log
from ...base import BaseHandler

from ....models import PublicRelease, PublicSourcePage

log = make_log('api/public_release')


class PublicReleaseHandler(BaseHandler):
    def validate_link_name(self, session, link_name, release_id):
        is_unique = (
            session.scalars(
                PublicRelease.select(session.user_or_token, mode="read").where(
                    PublicRelease.link_name == link_name,
                    PublicRelease.id != release_id if release_id is not None else True,
                )
            ).first()
            is None
        )
        if not is_unique:
            self.error("This link name is already in use")

        is_url_safe = bool(re.compile(r'^[0-9A-Za-z-_.+]+$').match(link_name))
        if not is_url_safe:
            self.error(
                "Link name must contain only "
                "alphanumeric characters, dashes, underscores, periods, or plus signs"
            )

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
                            linkName:
                                type: string
                            description:
                                type: string
                            options:
                                type: object
                            is_visible:
                                type: boolean
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
        link_name = data.get("link_name")
        if link_name is None or link_name == "":
            return self.error("Link name is required")

        with self.Session() as session:
            self.validate_link_name(session, link_name, None)

            public_release = PublicRelease(
                name=name,
                link_name=link_name,
                description=data.get("description", ""),
                options=data.get("options", {}),
                is_visible=data.get("is_visible", True),
            )
            session.add(public_release)
            session.commit()
            return self.success(data=public_release)

    def patch(self, release_id):
        """
        ---
        description: Update a public release
        tags:
          - public_release
        parameters:
          - in: path
            name: release_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  link_name:
                    type: string
                  description:
                    type: string
                  options:
                    type: object
                  is_visible:
                    type: boolean
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
        link_name = data.get("link_name")
        if link_name is None or link_name == "":
            return self.error("Link name is required")

        with self.Session() as session:
            public_release = session.scalars(
                PublicRelease.select(session.user_or_token, mode="update").where(
                    PublicRelease.id == release_id
                )
            ).first()

            if public_release is None:
                return self.error("Release not found", status=404)

            self.validate_link_name(session, link_name, release_id)

            public_release.name = name
            public_release.link_name = link_name
            public_release.description = data.get("description", "")
            public_release.options = data.get("options", {})
            public_release.is_visible = data.get("is_visible", True)
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

            if session.scalars(
                PublicSourcePage.select(session.user_or_token, mode="read").where(
                    PublicSourcePage.release_id == release_id
                )
            ).first():
                return self.error(
                    "Delete all sources associated before deleting this release",
                    status=400,
                )

            session.delete(public_release)
            session.commit()
            return self.success()
