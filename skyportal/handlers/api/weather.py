import datetime

import sqlalchemy as sa

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import Telescope, Weather
from ...utils.naive_datetime import utcnow_naive
from ...utils.offset import get_url
from ..base import BaseHandler

_, cfg = load_env()
weather_refresh = cfg.get("weather.refresh_time")
openweather_api_key = cfg.get("weather.openweather_api_key")


class WeatherHandler(BaseHandler):
    @auth_or_token
    async def get(self):
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
                            weather_fetch_at:
                              type: string
                              description: |
                                 Datetime (UTC) when the API call was made,
                                 even if no data was returned
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
          400:
            content:
              application/json:
                schema: Error
        """
        telescope_id = self.get_query_argument("telescope_id", None, type=int)
        async with self.AsyncSession() as session:
            # use the query telescope ID otherwise fall back to preferences id
            if telescope_id is None:
                user_prefs = (
                    getattr(self.associated_user_object, "preferences", None) or {}
                )
                pref_id = user_prefs.get("weather", {}).get("telescopeID")
                if pref_id is not None:
                    try:
                        telescope_id = int(pref_id)
                    except (TypeError, ValueError):
                        return self.error(
                            f"telescope ID ({pref_id}) "
                            f"given in preferences is not a valid ID (integer)."
                        )

            if telescope_id is not None:
                telescope = await session.scalar(
                    Telescope.select(self.current_user).where(
                        Telescope.id == telescope_id
                    )
                )
            else:
                # no ID requested and no preference: use the first accessible telescope
                telescope = await session.scalar(
                    Telescope.select(self.current_user).order_by(Telescope.id)
                )

            if telescope is None:
                if telescope_id is not None:
                    return self.error(
                        f"telescope with ID {telescope_id} not found or not accessible."
                    )
                else:
                    # if no ID requested, no preference and no telescopes accessible,
                    # respond gracefully so the widget can show "no weather information" instead of an error
                    return self.success(data={"weather": None})

            weather = await session.scalar(
                sa.select(Weather).where(Weather.telescope_id == telescope.id)
            )
            if weather is None:
                weather = Weather(telescope=telescope)
                session.add(weather)

            # Should we call the API again?
            refresh = weather_refresh is not None
            if refresh and weather.retrieved_at is not None:
                if (
                    weather.retrieved_at + datetime.timedelta(seconds=weather_refresh)
                    >= utcnow_naive()
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
                        weather.retrieved_at = utcnow_naive()
                        await session.commit()
                    else:
                        message = response.text

                await session.commit()

            return self.success(
                data={
                    "weather": weather.weather_info,
                    # Timestamp indicating when the weather data was successfully retrieved from the API
                    "weather_retrieved_at": weather.retrieved_at,
                    # Timestamp indicating when the API call was made, even if no data was returned
                    "weather_fetch_at": utcnow_naive(),
                    "weather_link": telescope.weather_link,
                    "telescope_name": telescope.name,
                    "telescope_nickname": telescope.nickname,
                    "telescope_id": telescope.id,
                    "message": message,
                }
            )
