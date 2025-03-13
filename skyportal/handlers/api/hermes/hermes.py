from baselayer.app.access import auth_or_token
from baselayer.app.handlers.base import BaseHandler


class Hermes(BaseHandler):
    @auth_or_token
    async def post(self):
        return

    @auth_or_token
    def get(self):
        return
