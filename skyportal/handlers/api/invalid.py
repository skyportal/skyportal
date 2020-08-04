from baselayer.app.access import auth_or_token
from ..base import BaseHandler


class InvalidEndpointHandler(BaseHandler):
    @auth_or_token
    def get(self, group_id=None):
        return self.error('Invalid API endpoint')
