import json
from baselayer.app.access import auth_or_token
from ...base import BaseHandler


class InstrumentObservationParamsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        with open("instrument_observation_params.json") as f:
            instrument_data = json.load(f)
        return self.success(data={"instrumentObsParams": instrument_data})
