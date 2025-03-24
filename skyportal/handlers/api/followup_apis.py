from baselayer.app.access import auth_or_token
from skyportal import facility_apis
from skyportal.enum_types import api_classnames

from ..base import BaseHandler

apis = {
    api_name: getattr(facility_apis, api_name).frontend_render_api_info()
    for api_name in api_classnames.enums
}


class FollowupAPIsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        return self.success(data=apis)
