import datetime

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from ...utils.offset import get_url

from ..base import BaseHandler
from ...models import DBSession, Telescope, Weather

_, cfg = load_env()
weather_refresh = cfg["weather"].get("refresh_time") if cfg.get("weather") else None
openweather_api_key = (
    cfg["weather"].get("openweather_api_key") if cfg.get("weather") else None
)

default_prefs = {'telescopeID': 1}


class WeatherHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve weather info at the telescope site saved by user
                     or telescope specified by `telescope_id` parameter
        tags:
          - weather
          - telescopes
        parameters:
            - in: query
              name: telescope_id
              required: false
              schema:
                type: integer
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            weather:
                              type: object
                              description: Open Weather Data
                            weather_retrieved_at:
                              type: string
                              description: |
                                 Datetime (UTC) when the weather was fetched
                            weather_link:
                              type: string
                              description: URL for more weather info
                            telescope_name:
                              type: string
                              description: Name of the telescope
                            telescope_nickname:
                              type: string
                              description: Short name of the telescope
                            telescope_id:
                              type: integer
                              description: Telescope ID
                            message:
                              type: string
                              description: Weather fetching error message
        """
        user_prefs = getattr(self.current_user, 'preferences', None) or {}
        weather_prefs = user_prefs.get('weather', {})
        weather_prefs = {**default_prefs, **weather_prefs}

        telescope_id = int(weather_prefs["telescopeID"])
        # use the query telecope ID otherwise fall back to preferences id
        telescope_id = self.get_query_argument("telescope_id", telescope_id)

        telescope = Telescope.get_if_accessible_by(telescope_id, self.current_user)
        if telescope is None:
            return self.error(
                f"Could not load telescope with ID {weather_prefs['telescopeID']}"
            )
        weather = Weather.query.filter(Weather.telescope_id == telescope_id).first()
        if weather is None:
            weather = Weather(telescope=telescope)
            DBSession().add(weather)

        # Should we call the API again?
        refresh = weather_refresh is not None
        if refresh and weather.retrieved_at is not None:
            if (
                weather.retrieved_at + datetime.timedelta(seconds=weather_refresh)
                >= datetime.datetime.utcnow()
            ):
                # it is too soon to refresh
                refresh = False
        elif weather.retrieved_at is None:
            refresh = True

        message = ""
        if refresh:
            response = get_url(
                "https://api.openweathermap.org/data/2.5/onecall?"
                f"lat={telescope.lat}&lon={telescope.lon}&appid={openweather_api_key}"
            )
            if response is not None:
                if response.status_code == 200:
                    data = response.json()
                    weather.weather_info = data
                    weather.retrieved_at = datetime.datetime.utcnow()
                    self.verify_and_commit()
                else:
                    message = response.text

        self.verify_and_commit()
        return self.success(
            data={
                "weather": weather.weather_info,
                "weather_retrieved_at": weather.retrieved_at,
                "weather_link": telescope.weather_link,
                "telescope_name": telescope.name,
                "telescope_nickname": telescope.nickname,
                "telescope_id": telescope.id,
                "message": message,
            }
        )
