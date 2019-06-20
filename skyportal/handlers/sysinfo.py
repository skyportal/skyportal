from .base import BaseHandler
from baselayer.app.access import auth_or_token
from ..models import Source, DBSession
import skyportal

import tornado.web


class SysInfoHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve system info
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        sources_table_empty:
                          type: boolean
                          description: Boolean indicating whether sources table is empty
                        version:
                          type: string
                          description: Current SkyPortal version
        """
        info = {
            'sources_table_empty': DBSession.query(Source).first() is None,
        }
        return self.success(data=info)
