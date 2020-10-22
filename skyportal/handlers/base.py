from baselayer.app.handlers.base import BaseHandler as BaselayerHandler
from .. import __version__


class BaseHandler(BaselayerHandler):
    @property
    def associated_user_object(self):
        if hasattr(self.current_user, "username"):
            return self.current_user
        return self.current_user.created_by

    def success(self, *args, **kwargs):
        super().success(*args, **kwargs, extra={'version': __version__})

    def error(self, message, *args, **kwargs):
        super().error(message, *args, **kwargs, extra={'version': __version__})
