from baselayer.app.handlers.base import BaseHandler
from baselayer.app.env import load_env


env, cfg = load_env()


class LoginErrorPageHandler(BaseHandler):
    def get(self):
        self.render("loginerror.html", app=cfg["app"])
