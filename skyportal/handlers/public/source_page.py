import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, sessionmaker

from baselayer.app.env import load_env

from ...models import DBSession, SourceAccessibility
from ...utils.cache import Cache
from ..base import BaseHandler

env, cfg = load_env()

Session = scoped_session(sessionmaker())

cache_dir = "cache/public_pages/sources"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_public_source_pages_cache"] * 60,
)

ALLOWED_PAGE_TYPES = ["source"]


class SourcePageHandler(BaseHandler):
    def get(self, page_type, page_id):
        """
        ---
        description: Retrieve all public source pages
        tags:
          - public_source_pages
        responses:
          200:
            content:
              application/json:
                schema: SourceAccessibility
          400:
            content:
              application/json:
                schema: Error
        """

        if page_type not in ALLOWED_PAGE_TYPES:
            return self.error(
                f"Invalid report type {page_type}, must be one of {ALLOWED_PAGE_TYPES}"
            )

        if page_id is None:
            return self.error(f"Page ID is required")

        cache_key = f"{page_type}_{page_id}"
        cached = cache[cache_key]
        if cached is None:
            return self.error(f"Page {page_id} not in cache")
            # if Session.registry.has():
            #     session = Session()
            # else:
            #     session = Session(bind=DBSession.session_factory.kw["bind"])

            # source_page = session.scalar(
            #     sa.select(SourceAccessibility).where(
            #         SourceAccessibility.source_id == page_id
            # )
            # if report is None:
            #     return self.error(f"Could not load GCN report {report_id}")
            # if not report.published:
            #     return self.error(f"GCN report {report_id} not yet published")
            # report.generate_report()
            # cached = cache[cache_key]

        data = np.load(cached, allow_pickle=True)
        data = data.item()
        if data['public']:
            self.set_header("Content-Type", "text/html; charset=utf-8")
            return self.write(data['html'])
        else:
            return self.error(f"This page is not available")
