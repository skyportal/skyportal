from collections import defaultdict
from sqlalchemy import func, literal
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import DBSession, Annotation


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
        annotations = func.jsonb_each(Annotation.data).table_valued("key", "value")

        # Objs are read-public, so no need to check that annotations belong to an unreadable obj
        # Instead, just check for annotation group membership
        q = DBSession().execute(
            Annotation.query_records_accessible_by(
                self.current_user, columns=[Annotation.origin]
            )
            .add_columns(
                annotations.c.key, func.jsonb_typeof(annotations.c.value).label("type")
            )
            .outerjoin(annotations, literal(True))
            .distinct()
        )

        # Restructure query results so that records are grouped by origin in a
        # nice, nested dictionary
        results = q.all()
        grouped = defaultdict(list)
        keys_seen = defaultdict(set)
        for annotation in results:
            if annotation.key not in keys_seen[annotation.origin]:
                grouped[annotation.origin].append({annotation.key: annotation.type})

            keys_seen[annotation.origin].add(annotation.key)

        return self.success(data=grouped)
