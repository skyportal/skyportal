import io
import traceback

import numpy as np

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ...utils.offset import finding_charts_cache
from ..base import BaseHandler

_, cfg = load_env()
log = make_log("api/source")


class CachedSourceFinderHandler(BaseHandler):
    @auth_or_token
    async def get(self, cache_key):
        """
        ---
        summary: Retrieve a cached finding chart
        description: Download a pre-generated PDF/PNG finding chart that has been cached
        tags:
          - sources
          - finding chart
          - public
        parameters:
          - in: path
            name: cache_key
            required: true
            schema:
              type: string
        responses:
          200:
            description: A PDF/PNG finding chart file
            content:
              application/pdf:
                schema:
                  type: string
                  format: binary
              image/png:
                schema:
                  type: string
                  format: binary
          400:
            content:
              application/json:
                schema: Error
        """

        try:
            value = finding_charts_cache[cache_key]
            if value is None:
                return self.error("Finding chart not found in cache", status=404)

            value = np.load(value, allow_pickle=True)
            value = value.item()

            filename = value["name"]
            data = io.BytesIO(value["data"])
            output_type = filename.split(".")[-1].lower()
        except Exception as e:
            # if its a value error with text "Source not found", we return a 404
            if isinstance(e, ValueError) and str(e) == "Source not found":
                return self.error("Source not found", status=404)

            # otherwise, we log the error and return a 500
            log(f"Error retrieving cached finding chart: {str(e)}")
            traceback.print_exc()
            return self.error(f"Error generating finding chart: {str(e)}")

        await self.send_file(data, filename, output_type=output_type)
