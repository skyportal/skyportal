import os
from baselayer.app.handlers.base import BaseHandler
from baselayer.app.env import load_env


env, cfg = load_env()


class LoginErrorPageHandler(BaseHandler):
    def get(self):
        if os.environ.get("PSA_ERROR_MSG"):
            error_message = str(os.environ.get("PSA_ERROR_MSG"))
            os.environ["PSA_ERROR_MSG"] = ""
        else:
            error_message = "Unable to retrieve authentication error message."
        self.render("loginerror.html", app=cfg["app"], error_message=error_message)
