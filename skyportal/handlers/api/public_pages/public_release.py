import operator  # noqa: F401
import re

from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log
from ...base import BaseHandler
from ....models import Group, PublicRelease, PublicSourcePage

log = make_log('api/public_release')


def process_link_name_validation(session, link_name, release_id):
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
        return False, "This link name is already in use"

    is_url_safe = bool(re.compile(r'^[0-9A-Za-z-_.+]+$').match(link_name))
    print(is_url_safe)
    if not is_url_safe:
        return (
            False,
            "Link name must contain only alphanumeric characters, dashes, underscores, periods, or plus signs",
        )

    return True, ""


class PublicReleaseHandler(BaseHandler):
    @permissions(['Manage sources'])
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
        groups = data.get("groups")
        if groups is None or len(groups) == 0:
            return self.error("Specify at least one group")

        with self.Session() as session:
            is_valid, message = process_link_name_validation(session, link_name, None)
            if not is_valid:
                return self.error(message)

            group_ids = [g.id for g in groups]
            if set(group_ids).issubset(
                [g.id for g in session.user_or_token.accessible_groups]
            ):
                groups = session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                ).all()

            if not groups:
                return self.error("Invalid groups")

            public_release = PublicRelease(
                name=name,
                link_name=link_name,
                description=data.get("description", ""),
                is_visible=data.get("is_visible", True),
                options=data.get("options", {}),
                groups=groups,
            )
            session.add(public_release)
            session.commit()
            return self.success(data=public_release)

    @permissions(['Manage sources'])
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
        groups = data.get("groups")
        if groups is None or len(groups) == 0:
            return self.error("Specify at least one group")

        with self.Session() as session:
            public_release = session.scalars(
                PublicRelease.select(session.user_or_token, mode="update").where(
                    PublicRelease.id == release_id
                )
            ).first()

            if public_release is None:
                return self.error("Release not found", status=404)

            is_valid, message = process_link_name_validation(
                session, link_name, release_id
            )
            if not is_valid:
                return self.error(message)

            group_ids = [g.id for g in groups]
            if set(group_ids).issubset(
                [g.id for g in session.user_or_token.accessible_groups]
            ):
                groups = session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                ).all()

            if not groups:
                return self.error("Invalid groups")

            public_release.name = name
            public_release.link_name = link_name
            public_release.description = data.get("description", "")
            public_release.is_visible = data.get("is_visible", True)
            public_release.options = data.get("options", {})
            public_release.groups = groups
            session.commit()
            return self.success(data=public_release)

    @auth_or_token
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
            public_releases = (
                session.execute(
                    PublicRelease.select(session.user_or_token, mode="read")
                    .options(joinedload(PublicRelease.groups))
                    .order_by(PublicRelease.name.asc())
                )
                .unique()
                .all()
            )
            return self.success(data=public_releases)

    @permissions(['Manage sources'])
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
