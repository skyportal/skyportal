import numpy as np
from sqlalchemy.orm import scoped_session, sessionmaker
import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.models import DBSession
from ...models.public_pages.public_source_page import PublicSourcePage

from ...utils.cache import Cache
from ..base import BaseHandler

env, cfg = load_env()

Session = scoped_session(sessionmaker())

cache_dir = "cache/public_pages/sources"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_public_source_pages_cache"] * 60,
)


def get_version(source_id, version_date):
    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])
    query = sa.select(PublicSourcePage).where(
        PublicSourcePage.source_id == source_id, PublicSourcePage.is_public
    )
    if version_date:
        query = query.where(PublicSourcePage.created_at_iso == version_date)
    else:
        query = query.order_by(PublicSourcePage.created_at.desc())
    return session.scalars(query).first()


class SourcePageHandler(BaseHandler):
    def get(self, source_id=None, version_date=None):
        """
        ---
        description: Display the public page for a given source and version
         or list all public source pages
        tags:
          - source_page
        parameters:
            - in: path
              name: source_id
              required: false
              schema:
                type: string
              description: The ID of the source for which to display the public page
            - in: path
              name: version_date
              required: false
              schema:
                type: string
              description: The date of the version of the public page to display
        responses:
            200:
              content:
                text/html:
                  schema:
                    type: string
                    description: The HTML content of the public source page
            400:
              content:
                application/json:
                  schema: Error
        """
        # If source_id is None, list all public source pages
        if source_id is None:
            if Session.registry.has():
                session = Session()
            else:
                session = Session(bind=DBSession.session_factory.kw["bind"])
            versions = session.scalars(
                sa.select(PublicSourcePage)
                .where(PublicSourcePage.is_public)
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

        # If version_date None, retrieve the latest version
        if version_date is None:
            version = get_version(source_id, None)
            if version is None:
                return self.error("Page not found", status=404)
            version_date = version.created_at_iso

        cache_key = f"source_{source_id}_version_{version_date}"
        cached = cache[cache_key]

        # If the page is not cached, generate it
        if cached is None:
            version = get_version(source_id, version_date)
            if version is None:
                return self.error("Page not found", status=404)
            version.generate_public_source_page()
            cache_key = f"source_{source_id}_version_{version_date}"
            cached = cache[cache_key]

        data = np.load(cached, allow_pickle=True)
        data = data.item()
        if data['public']:
            self.set_header("Content-Type", "text/html; charset=utf-8")
            return self.write(data['html'])
        else:
            return self.error("This page is not available", status=404)
