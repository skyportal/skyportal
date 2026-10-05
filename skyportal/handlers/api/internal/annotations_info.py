from collections import defaultdict

import numpy as np
from sqlalchemy import func, literal
from sqlalchemy.orm import aliased

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ....models import Annotation, GroupAnnotation
from ....utils.cache import Cache, cache_folder, dict_to_bytes
from ...base import BaseHandler

_, cfg = load_env()

cache_dir = f"{cache_folder}/annotations_info"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg.get("misc.minutes_to_keep_annotations_info_query_cache", 360)
    * 60,  # defaults to 6 hours
)

log = make_log("api/annotations_info")


class AnnotationsInfoHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        description: Collects valid annotation origin/key pairs to filter on for scanning
        parameters:
          - in: query
            name: groupIDs
            nullable: true
            schema:
              type: string
            description: |
              Comma-separated group IDs; only annotations shared with one of these
              groups are considered.
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

        group_ids = self.get_query_argument("groupIDs", None)
        try:
            group_ids = {int(g) for g in group_ids.split(",")} if group_ids else set()
        except ValueError:
            return self.error(f"Invalid groupIDs: {group_ids}")

        try:
            cache_key = f"annotations_info_by_group_{self.associated_user_object.id}"
            cached = cache[cache_key]
            if cached is not None:
                info = np.load(cached, allow_pickle=True).item()
            else:
                annotations = func.jsonb_each(Annotation.data).table_valued(
                    "key", "value"
                )
                group_annotation = aliased(GroupAnnotation)
                async with self.AsyncSession() as session:
                    # Objs are read-public, so no need to check that annotations belong to an unreadable obj
                    # Instead, just check for annotation group membership
                    keys_result = await session.execute(
                        Annotation.select(
                            session.user_or_token, columns=[Annotation.origin]
                        )
                        .add_columns(
                            annotations.c.key,
                            func.jsonb_typeof(annotations.c.value).label("type"),
                        )
                        .outerjoin(annotations, literal(True))
                        .distinct()
                    )
                    groups_result = await session.execute(
                        Annotation.select(
                            session.user_or_token, columns=[Annotation.origin]
                        )
                        .add_columns(group_annotation.group_id)
                        .join(
                            group_annotation,
                            group_annotation.annotation_id == Annotation.id,
                        )
                        .distinct()
                    )

                    # Restructure query results so that records are grouped by origin in a
                    # nice, nested dictionary
                    grouped = defaultdict(list)
                    keys_seen = defaultdict(set)
                    for annotation in keys_result.all():
                        if annotation.key not in keys_seen[annotation.origin]:
                            grouped[annotation.origin].append(
                                {annotation.key: annotation.type}
                            )

                        keys_seen[annotation.origin].add(annotation.key)

                    groups_by_origin = defaultdict(set)
                    for row in groups_result.all():
                        groups_by_origin[row.origin].add(row.group_id)

                info = {"keys": dict(grouped), "groups": dict(groups_by_origin)}
                cache[cache_key] = dict_to_bytes(info)

            return self.success(
                data={
                    origin: keys
                    for origin, keys in info["keys"].items()
                    if not group_ids or info["groups"].get(origin, set()) & group_ids
                }
            )

        except Exception as e:
            log(f"Failed to get annotations info: {e}")
            return self.error(f"Failed to get annotations info: {e}")
