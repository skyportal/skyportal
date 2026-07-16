import numpy as np
import sqlalchemy as sa

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ....utils.cache import Cache, dict_to_bytes
from ...base import BaseHandler

_, cfg = load_env()

cache_dir = "cache/altdata_info"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg.get("misc.minutes_to_keep_altdata_info_query_cache", 360)
    * 60,  # defaults to 6 hours
)

log = make_log("api/altdata_info")


class AltdataInfoHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        description: Collects the distinct top-level altdata keys (with value type)
          present on Objs, used to offer altdata columns on the sources table.
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            keys:
                              type: array
                              description: |
                                Array of { key: value_type } objects, one per
                                distinct top-level altdata key.
        """
        # Objs are read-public, so altdata keys are the same for every user and
        # can be cached globally.
        try:
            cache_key = "altdata_info"
            cached = cache[cache_key]
            if cached is not None:
                data = np.load(cached, allow_pickle=True)
                return self.success(data=data.item())

            # Filter to object-valued altdata first, then expand keys with a
            # LATERAL jsonb_each so scalar/NULL altdata never reaches the function.
            statement = sa.text(
                "SELECT DISTINCT je.key AS key, jsonb_typeof(je.value) AS type "
                "FROM (SELECT altdata FROM objs "
                "WHERE jsonb_typeof(altdata) = 'object') o, "
                "jsonb_each(o.altdata) AS je(key, value)"
            )
            async with self.AsyncSession() as session:
                result = await session.execute(statement)

                keys_seen = set()
                keys = []
                for row in result.all():
                    if row.key not in keys_seen:
                        keys.append({row.key: row.type})
                        keys_seen.add(row.key)

                data = {"keys": keys}
                cache[cache_key] = dict_to_bytes(data)
                return self.success(data=data)

        except Exception as e:
            log(f"Failed to get altdata info: {e}")
            return self.error(f"Failed to get altdata info: {e}")
