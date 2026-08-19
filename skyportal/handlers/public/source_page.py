from typing import Annotated

import numpy as np
import sqlalchemy as sa
from pydantic import Field

from baselayer.app.env import load_env
from baselayer.app.models import DBSession

from ...models.public_pages.public_release import PublicRelease
from ...models.public_pages.public_source_page import PublicSourcePage
from ...utils.cache import Cache
from ..base import BaseHandler

SourceId = Annotated[
    str, Field(description="The ID of the source for which to display the public page")
]
VersionHash = Annotated[
    str, Field(description="The hash of the source data used to identify the version")
]

env, cfg = load_env()

cache_dir = "cache/public_pages/sources"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_public_source_pages_cache"] * 60,
)


def get_version(session, release_name, source_id, version_hash):
    query = sa.select(PublicSourcePage).where(
        PublicSourcePage.source_id == source_id, PublicSourcePage.is_visible
    )
    if release_name:
        query = query.join(PublicRelease).where(
            PublicRelease.link_name == release_name, PublicRelease.is_visible
        )
    else:
        query = query.where(PublicSourcePage.release_id.is_(None))

    if version_hash:
        query = query.where(PublicSourcePage.hash == version_hash)
    else:
        query = query.order_by(PublicSourcePage.created_at.desc())
    return session.scalar(query)


class SourcePageHandler(BaseHandler):
    def get(self, source_id: SourceId = None, version_hash: VersionHash = None):
        """
        ---
        single:
            summary: Display the public page for a source
            description: Display the public page for a given source and version
            tags:
              - public
              - sources
            responses:
                200:
                  content:
                    text/html:
                      schema:
                        type: string
                        description: |
                            The HTML content of the selected version of the public source page
                            or the latest version if hash is not provided
                404:
                  content:
                    application/json:
                      schema: Error
        multiple:
            summary: List all public source pages
            description: List all public source pages with no release and their versions
            tags:
              - public
              - sources
            responses:
                200:
                  content:
                    text/html:
                      schema:
                        type: string
                        description: The HTML content of the page listing all public source pages
        """
        with DBSession() as session:
            # If source_id is None, list all public source pages with no release
            if source_id is None:
                versions = session.scalars(
                    sa.select(PublicSourcePage)
                    .where(
                        PublicSourcePage.is_visible,
                        PublicSourcePage.release_id.is_(None),
                    )
                    .order_by(PublicSourcePage.created_at.desc())
                ).all()
                versions_by_source = {}
                for version in versions:
                    if version.source_id not in versions_by_source:
                        versions_by_source[version.source_id] = []
                    versions_by_source[version.source_id].append(version)
                return self.render(
                    "public_pages/sources/sources_template.html",
                    versions_by_source=versions_by_source,
                )

            # If version_hash is None, retrieve the latest version of the source
            version = None
            if version_hash is None:
                version = get_version(session, None, source_id, None)
                if version is None:
                    return self.error("Page not found", status=404)
                version_hash = version.hash

            cache_key = f"source_{source_id}_version_{version_hash}"
            cached = cache[cache_key]

            # If the page is not cached, generate it
            if cached is None:
                if version is None:
                    version = get_version(session, None, source_id, version_hash)
                    if version is None:
                        return self.error("Page not found", status=404)
                version.generate_page()
                cache_key = f"source_{source_id}_version_{version_hash}"
                cached = cache[cache_key]

            data = np.load(cached, allow_pickle=True)
            data = data.item()
            if data["public"]:
                self.set_header("Content-Type", "text/html; charset=utf-8")
                return self.write(data["html"])
            else:
                return self.error("Page not found", status=404)


class ReleaseSourcePageHandler(BaseHandler):
    def get(
        self,
        release_name: Annotated[
            str, Field(description="The link name of the public release to display")
        ],
        source_id: SourceId,
        version_hash: VersionHash,
    ):
        """
        ---
        summary: Display the public page for a source in a specific release
        description: Display the public page for a given source and version in a specific release
        tags:
            - public
            - sources
        responses:
            200:
              content:
                text/html:
                  schema:
                    type: string
                    description: The HTML content of the selected version of the public source page
            404:
              content:
                application/json:
                  schema: Error
        """
        with DBSession() as session:
            cache_key = (
                f"release_{release_name}_source_{source_id}_version_{version_hash}"
            )
            cached = cache[cache_key]

            # If the page is not cached, generate it
            if cached is None:
                version = get_version(session, release_name, source_id, version_hash)
                if version is None:
                    return self.error("Page not found", status=404)
                version.generate_page()
                cache_key = (
                    f"release_{release_name}_source_{source_id}_version_{version_hash}"
                )
                cached = cache[cache_key]

            data = np.load(cached, allow_pickle=True)
            data = data.item()
            if data["public"]:
                self.set_header("Content-Type", "text/html; charset=utf-8")
                return self.write(data["html"])
            else:
                return self.error("Page not found", status=404)
