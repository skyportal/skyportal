from baselayer.app.handlers.base import BaseHandler as BaselayerHandler
from .. import __version__


class BaseHandler(BaselayerHandler):
    def success(self, *args, **kwargs):
        data = kwargs.get('data', {})
        data['version'] = __version__
        kwargs['data'] = data
        super().success(*args, **kwargs)

    def error(self, *args, **kwargs):
        data = kwargs.get('data', {})
        data['version'] = __version__
        kwargs['data'] = data
        super().error(*args, **kwargs)
