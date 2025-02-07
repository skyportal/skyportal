from baselayer.app.access import auth_or_token

from ..base import BaseHandler


class CandidateScanReportHandler(BaseHandler):
    @auth_or_token
    def get(self):
        return

    @auth_or_token
    def post(self):
        return

    @auth_or_token
    def delete(self):
        return
