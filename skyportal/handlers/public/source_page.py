import numpy as np
from sqlalchemy.orm import scoped_session, sessionmaker

from baselayer.app.env import load_env

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
    def get(self, source_id):
        """
        ---
        description: Display a public source page
        tags:
          - public_source_page
        parameters:
            - in: path
              name: source_id
              required: true
              schema:
                type: integer
              description: The ID of the source to display
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

        if source_id is None:
            self.error("Source ID required")

        cache_key = f"source_{source_id}"
        cached = cache[cache_key]
        if cached is None:
            self.error("Page not found", status=404)
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
            return self.error("This page is not available")
