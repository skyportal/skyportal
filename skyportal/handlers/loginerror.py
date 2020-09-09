from baselayer.app.handlers.base import BaseHandler


class LoginErrorPageHandler(BaseHandler):
    def get(self):
        self.render("loginerror.html")
