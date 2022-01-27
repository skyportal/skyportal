from ....models import Instrument
from baselayer.app.access import auth_or_token
from ...base import BaseHandler


class RoboticInstrumentsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        apitype = self.get_query_argument('apitype', 'api_classname')
        if apitype is not None:
            if apitype == "api_classname":
                instruments = (
                    Instrument.query_records_accessible_by(self.current_user)
                    .filter(Instrument.api_classname.isnot(None))
                    .all()
                )
                retval = {i.id: i.api_class.frontend_render_info() for i in instruments}
            elif apitype == "api_observationplan_classname":
                instruments = (
                    Instrument.query_records_accessible_by(self.current_user)
                    .filter(Instrument.api_observationplan_classname.isnot(None))
                    .all()
                )
                retval = {
                    i.id: i.api_observationplan_class.frontend_render_info()
                    for i in instruments
                }
            else:
                return self.error(
                    f"apitype can only be api_classname or api_observationplan_classname, not {apitype}"
                )
        instruments = (
            Instrument.query_records_accessible_by(self.current_user)
            .filter(Instrument.api_classname.isnot(None))
            .all()
        )
        retval = {i.id: i.api_class.frontend_render_info(i) for i in instruments}
        
        self.verify_and_commit()
        return self.success(data=retval)
