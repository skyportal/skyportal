from ....models import Instrument
from baselayer.app.access import auth_or_token
from ...base import BaseHandler


class RoboticInstrumentsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        apitype = self.get_query_argument('apiType', 'api_classname')
        if apitype is not None:
            if apitype == "api_classname":
                instruments = (
                    Instrument.query_records_accessible_by(self.current_user)
                    .filter(Instrument.api_classname.isnot(None))
                    .all()
                )
                retval = {
                    i.id: i.api_class.frontend_render_info(i, self.current_user)
                    for i in instruments
                }
            elif apitype == "api_classname_obsplan":
                instruments = (
                    Instrument.query_records_accessible_by(self.current_user)
                    .filter(Instrument.api_classname_obsplan.isnot(None))
                    .all()
                )
                retval = {
                    i.id: i.api_class_obsplan.frontend_render_info(i, self.current_user)
                    for i in instruments
                }
            else:
                return self.error(
                    f"apitype can only be api_classname or api_classname_obsplan, not {apitype}"
                )

        self.verify_and_commit()
        return self.success(data=retval)
