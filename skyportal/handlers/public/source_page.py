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


class SourcePageHandler(BaseHandler):
    def get(self, request, source_id=None, version=None):
        """
        ---
        description: Display the public page for a given source
        tags:
          - public_source_page
        parameters:
            - in: path
              name: source_id
              required: false
              schema:
                type: integer
              description: The ID of the source for which to display the public page
            - in: path
              name: version
              required: false
              schema:
                type: string
                description: The version of the public page to display
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
        if source_id is None:
            if Session.registry.has():
                session = Session()
            else:
                session = Session(bind=DBSession.session_factory.kw["bind"])
            sources = session.scalars(
                sa.select(PublicSourcePage)
                .where(PublicSourcePage.is_public)
                .order_by(
                    PublicSourcePage.source_id, PublicSourcePage.created_at.desc()
                )
            ).all()
            return self.render(
                "public_pages/sources/sources_template.html", sources=sources
            )

        if version is None:
            if Session.registry.has():
                session = Session()
            else:
                session = Session(bind=DBSession.session_factory.kw["bind"])
            version = session.scalars(
                sa.select(PublicSourcePage.creation_date)
                .where(PublicSourcePage.source_id == source_id)
                .order_by(PublicSourcePage.created_at.desc())
            ).first()
            if version is None:
                return self.error("Page not found", status=404)

        cache_key = f"source_{source_id}_version_{version}"
        cached = cache[cache_key]
        # TODO: Implement cache management
        if cached is None:
            return self.error("Page not found", status=404)

        data = np.load(cached, allow_pickle=True)
        data = data.item()
        if data['public']:
            self.set_header("Content-Type", "text/html; charset=utf-8")
            return self.write(data['html'])
        else:
            return self.error("This page is not available")
