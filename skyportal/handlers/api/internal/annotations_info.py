from collections import defaultdict

import numpy as np
from sqlalchemy import func, literal

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ....models import Annotation
from ....utils.cache import Cache, dict_to_bytes
from ...base import BaseHandler

_, cfg = load_env()

cache_dir = "cache/annotations_info"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg.get("misc.minutes_to_keep_annotations_info_query_cache", 360)
    * 60,  # defaults to 6 hours
)

log = make_log("api/annotations_info")


class AnnotationsInfoHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Collects valid annotation origin/key pairs to filter on for scanning
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
                            description: |
                                An object in which each key is an annotation origin, and
                                the values are arrays of { key: value_type } objects
        """
        # This query gets the origin/keys present in the accessible annotaions
        # for an Obj, as well as the data type for the values for each key.
        # This information is used to generate the front-end form for selecting
        # filters to apply on the auto-annotations column on the scanning page.
        # For example, if given that an annotation field is numeric we should
        # have min/max fields on the form.

        try:
            cache_key = f"annotations_info_{self.associated_user_object.id}"
            cached = cache[cache_key]
            if cached is not None:
                data = np.load(cached, allow_pickle=True)
                return self.success(data=data.item())
            else:
                annotations = func.jsonb_each(Annotation.data).table_valued(
                    "key", "value"
                )
                with self.Session() as session:
                    # Objs are read-public, so no need to check that annotations belong to an unreadable obj
                    # Instead, just check for annotation group membership
                    results = session.execute(
                        Annotation.select(
                            session.user_or_token, columns=[Annotation.origin]
                        )
                        .add_columns(
                            annotations.c.key,
                            func.jsonb_typeof(annotations.c.value).label("type"),
                        )
                        .outerjoin(annotations, literal(True))
                        .distinct()
                    ).all()

                    # Restructure query results so that records are grouped by origin in a
                    # nice, nested dictionary
                    grouped = defaultdict(list)
                    keys_seen = defaultdict(set)
                    for annotation in results:
                        if annotation.key not in keys_seen[annotation.origin]:
                            grouped[annotation.origin].append(
                                {annotation.key: annotation.type}
                            )

                        keys_seen[annotation.origin].add(annotation.key)

                    cache[cache_key] = dict_to_bytes(grouped)
                    return self.success(data=grouped)

        except Exception as e:
            log(f"Failed to get annotations info: {e}")
            return self.error(f"Failed to get annotations info: {e}")
