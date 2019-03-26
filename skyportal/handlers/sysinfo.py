from baselayer.app.handlers.base import BaseHandler
from baselayer.app.access import auth_or_token
from ..models import Source, DBSession
import skyportal

import tornado.web


class SysInfoHandler(BaseHandler):
    @auth_or_token
    def get(self):
        info = {}
        info['sources_table_empty'] = DBSession.query(Source).first() is None
        info['skyportal_version'] = skyportal.__version__
        return self.success(info)
