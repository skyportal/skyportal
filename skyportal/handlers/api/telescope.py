import datetime

from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from ...utils.offset import get_url

from ..base import BaseHandler
from ...models import DBSession, Telescope

_, cfg = load_env()
weather_refresh = cfg["weather"].get("refresh_time") if cfg.get("weather") else None
openweather_api_key = (
    cfg["weather"].get("openweather_api_key") if cfg.get("weather") else None
)


class WeatherHandler(BaseHandler):
    @auth_or_token
    def get(self, telescope_id):
        """
        ---
        description: Retrieve weather at a telescope site
        parameters:
          - in: path
            name: telescope_id
            required: true
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
                            name:
                              type: string
                              description: Name of the telescope
                            nickname:
                              type: string
                              description: Short name of the telescope
        """
        t = Telescope.query.get(int(telescope_id))
        if t is None:
            return self.error(f"Could not load telescope with ID {telescope_id}")

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

        return self.success(
            data={
                "weather": t.weather,
                "weather_retrieved_at": t.weather_retrieved_at,
                "weather_link": t.weather_link,
                "name": t.name,
                "nickname": t.nickname,
                "message": message,
            }
        )


class TelescopeHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Create telescopes
        requestBody:
          content:
            application/json:
              schema: TelescopeNoID
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
                            id:
                              type: integer
                              description: New telescope ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        schema = Telescope.__schema__()

        try:
            telescope = schema.load(data)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        DBSession().add(telescope)
        DBSession().commit()

        return self.success(data={"id": telescope.id})

    @auth_or_token
    def get(self, telescope_id=None):
        """
        ---
        single:
          description: Retrieve a telescope
          parameters:
            - in: path
              name: telescope_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleTelescope
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all telescopes
          parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by name (exact match)
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfTelescopes
            400:
              content:
                application/json:
                  schema: Error
        """
        if telescope_id is not None:
            t = Telescope.query.get(int(telescope_id))
            if t is None:
                return self.error(f"Could not load telescope with ID {telescope_id}")
            return self.success(data=t)
        tel_name = self.get_query_argument("name", None)
        query = Telescope.query
        if tel_name is not None:
            query = query.filter(Telescope.name == tel_name)
        return self.success(data=query.all())

    @permissions(['Manage sources'])
    def put(self, telescope_id):
        """
        ---
        description: Update telescope
        parameters:
          - in: path
            name: telescope_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: TelescopeNoID
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        t = Telescope.query.get(int(telescope_id))
        if t is None:
            return self.error('Invalid telescope ID.')
        data = self.get_json()
        data['id'] = int(telescope_id)

        schema = Telescope.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        DBSession().commit()

        return self.success()

    @permissions(['Manage sources'])
    def delete(self, telescope_id):
        """
        ---
        description: Delete a telescope
        parameters:
          - in: path
            name: telescope_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        t = Telescope.query.get(int(telescope_id))
        if t is None:
            return self.error('Invalid telescope ID.')

        DBSession().query(Telescope).filter(Telescope.id == int(telescope_id)).delete()
        DBSession().commit()

        return self.success()
