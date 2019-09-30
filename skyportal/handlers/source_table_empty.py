from .base import BaseHandler
from baselayer.app.access import auth_or_token
from ..models import Source, DBSession
import skyportal

import tornado.web


class SourceTableEmptyHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Determine whether sources table is empy.
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        source_table_empty:
                          type: boolean
                          description: Boolean indicating whether source table is empty
        """
        info = {
            'source_table_empty': DBSession.query(Source).first() is None,
        }
        return self.success(data=info)
