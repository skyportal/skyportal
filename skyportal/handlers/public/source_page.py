import numpy as np
import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.models import DBSession
from ...models.public_pages.public_source_page import PublicSourcePage

from ...utils.cache import Cache
from ..base import BaseHandler

env, cfg = load_env()

cache_dir = "cache/public_pages/sources"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_public_source_pages_cache"] * 60,
)


def get_version(session, source_id, version_hash):
    query = sa.select(PublicSourcePage).where(
        PublicSourcePage.source_id == source_id, PublicSourcePage.is_visible
    )
    if version_hash:
        query = query.where(PublicSourcePage.hash == version_hash)
    else:
        query = query.order_by(PublicSourcePage.created_at.desc())
    return session.scalars(query).first()


class SourcePageHandler(BaseHandler):
    def get(self, source_id=None, version_hash=None):
        """
        ---
        single:
            description: Display the public page for a given source and version
            tags:
              - source_page
            parameters:
                - in: path
                  name: source_id
                  required: true
                  schema:
                    type: string
                  description: The ID of the source for which to display the public page
                - in: path
                  name: version_hash
                  required: true
                  schema:
                    type: string
                  description: The hash of the source data used to identify the version
            responses:
                200:
                  content:
                    text/html:
                      schema:
                        type: string
                        description: |
                            The HTML content of the selected version of the public source page
                            or the latest version if hash is not provided
                400:
                  content:
                    application/json:
                      schema: Error
        multiple:
            description: List all public source pages and their versions
            tags:
              - sources_page
            responses:
                200:
                  content:
                    text/html:
                      schema:
                        type: string
                        description: The HTML content of the page listing all public source pages
        """
        with DBSession() as session:
            # If source_id is None, list all public source pages
            if source_id is None:
                versions = session.scalars(
                    sa.select(PublicSourcePage)
                    .where(PublicSourcePage.is_visible)
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
                version = get_version(session, source_id, None)
                if version is None:
                    return self.error("Page not found", status=404)
                version_hash = version.hash

            cache_key = f"source_{source_id}_version_{version_hash}"
            cached = cache[cache_key]

            # If the page is not cached, generate it
            if cached is None:
                if version is None:
                    version = get_version(session, source_id, version_hash)
                    if version is None:
                        return self.error("Page not found", status=404)
                version.generate_page()
                cache_key = f"source_{source_id}_version_{version_hash}"
                cached = cache[cache_key]

            data = np.load(cached, allow_pickle=True)
            data = data.item()
            if data['public']:
                self.set_header("Content-Type", "text/html; charset=utf-8")
                return self.write(data['html'])
            else:
                return self.error("This page is not available", status=404)
