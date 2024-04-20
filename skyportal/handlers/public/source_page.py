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
        description: Display the public page for a given source
        tags:
          - public_source_page
        parameters:
            - in: path
              name: source_id
              required: true
              schema:
                type: integer
              description: The ID of the source for which to display the public page
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
            return self.error("Source ID required")

        cache_key = f"source_{source_id}"
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
