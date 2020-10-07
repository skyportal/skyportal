import datetime

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from ...utils.offset import get_url

from ..base import BaseHandler
from ...models import DBSession, Telescope

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
        description: Retrieve weather at a telescope site for the user
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
                            name:
                              type: string
                              description: Name of the telescope
                            nickname:
                              type: string
                              description: Short name of the telescope
        """
        user_prefs = getattr(self.current_user, 'preferences', None) or {}
        weather_prefs = user_prefs.get('weather', {})
        weather_prefs = {**default_prefs, **weather_prefs}

        t = Telescope.query.get(int(weather_prefs["telescopeID"]))
        if t is None:
            return self.error(
                f"Could not load telescope with ID {weather_prefs['telescopeID']}"
            )

        # Should we call the API again?
        refresh = weather_refresh is not None
        if refresh and t.weather_retrieved_at is not None:
            if (
                t.weather_retrieved_at + datetime.timedelta(seconds=weather_refresh)
                >= datetime.datetime.utcnow()
            ):
                # it is too soon to refresh
                refresh = False

        message = ""
        if refresh:
            response = get_url(
                "https://api.openweathermap.org/data/2.5/onecall?"
                f"lat={t.lat}&lon={t.lon}&appid={openweather_api_key}"
            )
            if response is not None:
                if response.status_code == 200:
                    weather = response.json()
                    t.weather = weather
                    t.weather_retrieved_at = datetime.datetime.utcnow()
                    DBSession().commit()
                else:
                    message = response.text

        return self.success(data={**t.to_dict(), "message": message})
