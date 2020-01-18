from baselayer.app.access import auth_or_token

from ...base import BaseHandler


import tornado.web

class ConfigHandler(BaseHandler):
    def initialize(self, **config):
        self.config = config

    @auth_or_token
    def get(self):
        """
        ---
        description: Return frontend configuration.
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
        """
        return self.success(data={'config': self.config})
