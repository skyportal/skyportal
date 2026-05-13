from baselayer.app.access import auth_or_token

from ..base import BaseHandler


class InvalidEndpointHandler(BaseHandler):
    @auth_or_token
    async def get(self, *ignored_args):
        return self.error("Invalid API endpoint")
