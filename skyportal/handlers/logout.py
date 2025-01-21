from baselayer.app.access import auth_or_token

from .base import BaseHandler


class LogoutHandler(BaseHandler):
    @auth_or_token
    def get(self):
        self.clear_cookie("user_id")
        # Not strictly speaking necessary -- upon next websocket connection,
        # auth will fail and token will refresh
        self.clear_cookie("auth_token")
        self.redirect("/")
