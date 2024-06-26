import sqlalchemy as sa

from baselayer.app.models import DBSession
from ...models.public_pages.public_source_page import PublicSourcePage
from ...models.public_pages.public_release import PublicRelease

from ..base import BaseHandler


class ReleaseHandler(BaseHandler):
    def get(self, release_id=None):
        """
        ---
        single:
            description: Display the page with all sources and descriptions for a given public release
            tags:
              - release
            parameters:
                - in: path
                  name: release_id
                  required: true
                  schema:
                    type: string
                  description: The ID of the release to display
            responses:
                200:
                  content:
                    text/html:
                      schema:
                        type: string
                        description: The HTML content of the selected release page
                404:
                  content:
                    application/json:
                      schema: Error
        multiple:
            description: Display the page with all the public releases
            tags:
              - release
            responses:
                200:
                  content:
                    text/html:
                      schema:
                        type: string
                        description: The HTML content of the page with a list of all public releases
        """
        with DBSession() as session:
            if release_id is None:
                releases = session.scalars(
                    sa.select(PublicRelease)
                    .where(PublicRelease.is_visible)
                    .order_by(PublicRelease.name.asc())
                ).all()
                return self.render(
                    "public_pages/releases/releases_template.html",
                    releases=releases,
                )

            release = session.scalars(
                sa.select(PublicRelease).where(
                    PublicRelease.id == release_id, PublicRelease.is_visible
                )
            ).first()

            if release is None:
                return self.error("Page not found", status=404)

            versions = session.scalars(
                sa.select(PublicSourcePage)
                .where(
                    PublicSourcePage.is_visible,
                    PublicSourcePage.release_id == release_id,
                )
                .order_by(PublicSourcePage.created_at.desc())
            ).all()
            versions_by_source = {}
            for version in versions:
                if version.source_id not in versions_by_source:
                    versions_by_source[version.source_id] = []
                versions_by_source[version.source_id].append(version)

            return self.render(
                "public_pages/releases/release/release_template.html",
                release=release,
                versions_by_source=versions_by_source,
            )
