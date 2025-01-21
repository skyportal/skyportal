import datetime

import sqlalchemy as sa

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import Telescope, Weather
from ...utils.offset import get_url
from ..base import BaseHandler

_, cfg = load_env()
weather_refresh = cfg.get("weather.refresh_time")
openweather_api_key = cfg.get("weather.openweather_api_key")

default_prefs = {"telescopeID": 1}


class WeatherHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        summary: Get weather info at telescope site
        description: Retrieve weather info at the telescope site saved by user
                     or telescope specified by `telescope_id` parameter
        tags:
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
        with self.Session() as session:
            user_prefs = getattr(self.associated_user_object, "preferences", None) or {}
            weather_prefs = user_prefs.get("weather", {})
            weather_prefs = {**default_prefs, **weather_prefs}

            try:
                default_telescope_id = int(weather_prefs["telescopeID"])
            except (TypeError, ValueError):
                return self.error(
                    f"telescope ID ({weather_prefs['telescopeID']}) "
                    f"given in preferences is not a valid ID (integer)."
                )

            # use the query telecope ID otherwise fall back to preferences id
            telescope_id = self.get_query_argument("telescope_id", default_telescope_id)

            telescope = session.scalars(
                Telescope.select(self.current_user).where(Telescope.id == telescope_id)
            ).first()
            if telescope is None:
                return self.error(
                    f"Could not load telescope with ID {weather_prefs['telescopeID']}"
                )

            weather = session.scalars(
                sa.select(Weather).where(Weather.telescope_id == telescope_id)
            ).first()
            if weather is None:
                weather = Weather(telescope=telescope)
                session.add(weather)

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
                    "https://api.openweathermap.org/data/3.0/onecall?"
                    f"lat={telescope.lat}&lon={telescope.lon}&appid={openweather_api_key}"
                )
                if response is not None:
                    if response.status_code == 200:
                        data = response.json()
                        weather.weather_info = data
                        weather.retrieved_at = datetime.datetime.utcnow()
                        session.commit()
                    else:
                        message = response.text

                session.commit()

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
