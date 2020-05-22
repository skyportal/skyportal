from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ... import __version__


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
        """
        info = {
            'version': __version__
        }
        return self.success(data=info)
