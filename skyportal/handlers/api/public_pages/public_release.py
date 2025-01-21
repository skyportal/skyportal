import operator  # noqa: F401
import re

from sqlalchemy import func

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ....models import Group, GroupPublicRelease, PublicRelease, PublicSourcePage
from ...base import BaseHandler

log = make_log("api/public_release")


def process_link_name_validation(session, link_name, release_id):
    is_unique = (
        session.scalar(
            PublicRelease.select(session.user_or_token, mode="read").where(
                PublicRelease.link_name == link_name,
                PublicRelease.id != release_id if release_id is not None else True,
            )
        )
        is None
    )
    if not is_unique:
        return False, "This link name is already in use"

    is_url_safe = bool(re.compile(r"^[0-9A-Za-z-_.+]+$").match(link_name))
    if not is_url_safe:
        return (
            False,
            "Link name must contain only alphanumeric characters, dashes, underscores, periods, or plus signs",
        )

    return True, ""


class PublicReleaseHandler(BaseHandler):
    @permissions(["Manage sources"])
    async def post(self):
        """
        ---
          summary: Create a new public release
          description:
            Create a new public release
          tags:
            - public
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
                    group_ids:
                      type: array
                      items:
                      type: integer
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
        group_ids = data.get("group_ids")
        if group_ids is None or len(group_ids) == 0:
            return self.error("Specify at least one group")

        with self.Session() as session:
            is_valid, message = process_link_name_validation(session, link_name, None)
            if not is_valid:
                return self.error(message)

            if set(group_ids).issubset(
                [g.id for g in self.current_user.accessible_groups]
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
            self.push_all(action="skyportal/REFRESH_PUBLIC_RELEASES")
            return self.success()

    @permissions(["Manage sources"])
    def patch(self, release_id):
        """
        ---
        summary: Update a public release
        description: Update a public release
        tags:
          - public
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
                  group_ids:
                    type: array
                    items:
                      type: integer
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
        group_ids = data.get("group_ids")
        if group_ids is None or len(group_ids) == 0:
            return self.error("Specify at least one group")

        with self.Session() as session:
            public_release = session.scalar(
                PublicRelease.select(session.user_or_token, mode="update").where(
                    PublicRelease.id == release_id
                )
            )

            if public_release is None:
                return self.error("Release not found", status=404)

            if set(group_ids).issubset(
                [g.id for g in self.current_user.accessible_groups]
            ):
                groups = session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                ).all()

            if not groups:
                return self.error("Invalid groups")

            if (
                data.get("is_visible", False) is False
                and public_release.is_visible is True
            ):
                for source_page in public_release.source_pages:
                    source_page.remove_from_cache()

            public_release.name = name
            public_release.description = data.get("description", "")
            public_release.is_visible = data.get("is_visible", True)
            public_release.options = data.get("options", {})
            public_release.groups = groups
            session.commit()

            self.push_all(action="skyportal/REFRESH_PUBLIC_RELEASES")
            return self.success()

    @auth_or_token
    def get(self):
        """
        ---
          summary: Get all public releases
          description:
            Retrieve all public releases
          tags:
            - public
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
                session.scalars(
                    PublicRelease.select(session.user_or_token, mode="read").order_by(
                        PublicRelease.name.asc()
                    )
                )
                .unique()
                .all()
            )

            # Retrieve group ids associated with each release that the user has access to
            accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
            group_releases = (
                session.query(
                    GroupPublicRelease.publicrelease_id,
                    func.array_agg(GroupPublicRelease.group_id).label("group_ids"),
                )
                .where(GroupPublicRelease.group_id.in_(accessible_group_ids))
                .group_by(GroupPublicRelease.publicrelease_id)
                .all()
            )
            group_releases_dict = {
                r.publicrelease_id: r.group_ids for r in group_releases
            }

            for release in public_releases:
                release.group_ids = group_releases_dict.get(release.id, [])

            return self.success(data=public_releases)

    @permissions(["Manage sources"])
    def delete(self, release_id):
        """
        ---
        summary: Delete a public release
        description: Delete a public release
        tags:
          - public
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
            return self.error("Missing release id")

        with self.Session() as session:
            public_release = session.scalar(
                PublicRelease.select(session.user_or_token, mode="delete").where(
                    PublicRelease.id == release_id
                )
            )

            if public_release is None:
                return self.error("Release not found", status=404)

            if session.scalar(
                PublicSourcePage.select(session.user_or_token, mode="read").where(
                    PublicSourcePage.release_id == release_id
                )
            ):
                return self.error(
                    "Delete all sources associated before deleting this release",
                    status=400,
                )

            session.delete(public_release)
            session.commit()

            self.push_all(action="skyportal/REFRESH_PUBLIC_RELEASES")
            return self.success()
