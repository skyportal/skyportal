from baselayer.app.access import auth_or_token

from ..base import BaseHandler
from ...enum_types import (
    ALLOWED_SPECTRUM_TYPES,
    ALLOWED_MAGSYSTEMS,
    ALLOWED_BANDPASSES,
    THUMBNAIL_TYPES,
    FOLLOWUP_PRIORITIES,
    ALLOWED_API_CLASSNAMES,
)


class EnumTypesHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve enum types in the DB
        tags:
          - system_info
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
                            ALLOWED_SPECTRUM_TYPES:
                              type: array
                              description: list of allowed spectrum types
                            ALLOWED_MAGSYSTEMS:
                              type: array
                              description: list of allowed magnitude systems
                            ALLOWED_BANDPASSES:
                              type: array
                              description: list of allowed bandpasses
                            THUMBNAIL_TYPES:
                              type: array
                              description: list of allowed thumbnail types
                            FOLLOWUP_PRIORITIES:
                              type: array
                              description: list of allowed followup priorities
                            ALLOWED_API_CLASSNAMES:
                              type: array
                              description: list of allowed API classnames
        """
        data = {}
        data["ALLOWED_SPECTRUM_TYPES"] = ALLOWED_SPECTRUM_TYPES
        data["ALLOWED_MAGSYSTEMS"] = ALLOWED_MAGSYSTEMS
        data["ALLOWED_BANDPASSES"] = ALLOWED_BANDPASSES
        data["THUMBNAIL_TYPES"] = THUMBNAIL_TYPES
        data["FOLLOWUP_PRIORITIES"] = FOLLOWUP_PRIORITIES
        data["ALLOWED_API_CLASSNAMES"] = ALLOWED_API_CLASSNAMES
        return self.success(data=data)
