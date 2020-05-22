from baselayer.app.handlers.base import BaseHandler as BaselayerHandler
from .. import __version__


class BaseHandler(BaselayerHandler):
    def success(self, *args, **kwargs):
        super().success(*args, **kwargs,
                        extra={'version': __version__})

    def error(self, *args, **kwargs):
        super().error(*args, **kwargs,
                      extra={'version': __version__})
