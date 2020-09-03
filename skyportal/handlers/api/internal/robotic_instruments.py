from ....models import Instrument
from baselayer.app.access import auth_or_token
from ...base import BaseHandler


class RoboticInstrumentsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        instruments = Instrument.query.filter(
            Instrument.api_classname.isnot(None)
        ).all()
        retval = {i.id: i.api_class.frontend_render_info() for i in instruments}
        return self.success(data=retval)
