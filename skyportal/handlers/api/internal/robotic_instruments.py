from ....models import Instrument
from baselayer.app.access import auth_or_token
from ...base import BaseHandler


class RoboticInstrumentsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        apitype = self.get_query_argument('apiType', 'api_classname')
        with self.Session() as session:
            if apitype is not None:
                if apitype == "api_classname":
                    instruments = session.scalars(
                        Instrument.select(session.user_or_token).where(
                            Instrument.api_classname.isnot(None)
                        )
                    ).all()
                    retval = {
                        i.id: i.api_class.frontend_render_info(i, self.current_user)
                        for i in instruments
                    }
                elif apitype == "api_classname_obsplan":
                    instruments = session.scalars(
                        Instrument.select(session.user_or_token).where(
                            Instrument.api_classname_obsplan.isnot(None)
                        )
                    ).all()
                    retval = {
                        i.id: i.api_class_obsplan.frontend_render_info(
                            i, self.current_user
                        )
                        for i in instruments
                    }
                else:
                    return self.error(
                        f"apitype can only be api_classname or api_classname_obsplan, not {apitype}"
                    )
            return self.success(data=retval)
