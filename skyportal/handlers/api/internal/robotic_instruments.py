from ....models import Instrument
from baselayer.app.access import auth_or_token
from ...base import BaseHandler


class RoboticInstrumentsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        instruments = (
            Instrument.query_records_accessible_by(self.current_user)
            .filter(Instrument.api_classname.isnot(None))
            .all()
        )
        retval = {i.id: i.api_class.frontend_render_info(i) for i in instruments}
        self.verify_and_commit()
        return self.success(data=retval)
