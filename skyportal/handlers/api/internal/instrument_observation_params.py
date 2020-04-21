import json
from baselayer.app.access import auth_or_token
from ...base import BaseHandler


class InstrumentObservationParamsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        try:
            with open("instrument_observation_params.json") as f:
                instrument_data = json.load(f)
        except FileNotFoundError:
            return self.error("instrument_observation_params.json does not exist.")
        except json.JSONDecodeError:
            return self.error("JSON parse error: instrument_observation_params.json "
                              "does not contain properly formatted JSON.")
        return self.success(data={"instrumentObsParams": instrument_data})
