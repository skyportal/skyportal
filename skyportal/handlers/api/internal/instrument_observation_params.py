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
            return self.error("Instrument observation parameters file does not exist.")
        except json.JSONDecodeError:
            return self.error(
                "JSON parse error: instrument observation parameters file "
                "does not contain properly formatted JSON."
            )
        return self.success(data=instrument_data)
