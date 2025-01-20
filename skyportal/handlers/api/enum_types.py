from baselayer.app.access import auth_or_token

from ...enum_types import (
    ALLOWED_API_CLASSNAMES,
    ALLOWED_BANDPASSES,
    ALLOWED_MAGSYSTEMS,
    ALLOWED_SPECTRUM_TYPES,
    ANALYSIS_INPUT_TYPES,
    ANALYSIS_TYPES,
    AUTHENTICATION_TYPES,
    FOLLOWUP_PRIORITIES,
    THUMBNAIL_TYPES,
)
from ..base import BaseHandler


class EnumTypesHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        summary: Get enum types in the DB
        description: Retrieve enum types in the DB
        tags:
          - system info
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
                            ANALYSIS_TYPES:
                              type: array
                              description: list of analysis types
                            ANALYSIS_INPUT_TYPES:
                              type: array
                              description: list of analysis input types
                            AUTHENTICATION_TYPES:
                              type: array
                              description: list of authentication types
        """
        data = {}
        data["ALLOWED_SPECTRUM_TYPES"] = ALLOWED_SPECTRUM_TYPES
        data["ALLOWED_MAGSYSTEMS"] = ALLOWED_MAGSYSTEMS
        data["ALLOWED_BANDPASSES"] = ALLOWED_BANDPASSES
        data["THUMBNAIL_TYPES"] = THUMBNAIL_TYPES
        data["FOLLOWUP_PRIORITIES"] = FOLLOWUP_PRIORITIES
        data["ALLOWED_API_CLASSNAMES"] = ALLOWED_API_CLASSNAMES
        data["ANALYSIS_TYPES"] = ANALYSIS_TYPES
        data["ANALYSIS_INPUT_TYPES"] = ANALYSIS_INPUT_TYPES
        data["AUTHENTICATION_TYPES"] = AUTHENTICATION_TYPES
        return self.success(data=data)
