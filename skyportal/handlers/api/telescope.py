from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token

from ..base import BaseHandler
from ...models import Telescope


class TelescopeHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Create telescopes
        tags:
          - telescopes
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

        with self.Session() as session:

            schema = Telescope.__schema__()
            # check if the telescope has a fixed location
            if 'fixed_location' in data:
                if data['fixed_location']:
                    if (
                        'lat' not in data
                        or 'lon' not in data
                        or 'elevation' not in data
                    ):
                        return self.error(
                            'Missing latitude, longitude, or elevation; required if the telescope is fixed'
                        )
                    elif (
                        not isinstance(data['lat'], (int, float))
                        or not isinstance(data['lon'], (int, float))
                        or not isinstance(data['elevation'], (int, float))
                    ):
                        return self.error(
                            'Latitude, longitude, and elevation must all be numbers'
                        )
                    elif (
                        data['lat'] < -90
                        or data['lat'] > 90
                        or data['lon'] < -180
                        or data['lon'] > 180
                        or data['elevation'] < 0
                    ):
                        return self.error(
                            'Latitude must be between -90 and 90, longitude between -180 and 180, and elevation must be positive'
                        )
            try:
                telescope = schema.load(data)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )
            session.add(telescope)
            session.commit()

            self.push_all(action="skyportal/REFRESH_TELESCOPES")
            return self.success(data={"id": telescope.id})

    @auth_or_token
    def get(self, telescope_id=None):
        """
        ---
        single:
          description: Retrieve a telescope
          tags:
            - telescopes
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
          tags:
            - telescopes
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

        with self.Session() as session:

            if telescope_id is not None:
                t = session.scalars(
                    Telescope.select(session.user_or_token).where(
                        Telescope.id == int(telescope_id)
                    )
                ).first()
                if t is None:
                    return self.error(
                        f"Could not load telescope with ID {telescope_id}"
                    )
                return self.success(data=t)

            tel_name = self.get_query_argument("name", None)
            stmt = Telescope.select(session.user_or_token)
            if tel_name is not None:
                stmt = stmt.where(Telescope.name == tel_name)

            data = session.scalars(stmt).all()
            telescopes = []
            for telescope in data:
                if telescope is None:
                    continue
                temp = telescope.to_dict()
                morning = False
                evening = False
                is_night_astronomical = False
                if (
                    telescope.fixed_location
                    and telescope.lon is not None
                    and telescope.lat is not None
                    and telescope.elevation is not None
                    and telescope.observer is not None
                ):
                    try:
                        morning = telescope.next_twilight_morning_astronomical()
                        evening = telescope.next_twilight_evening_astronomical()
                        if morning is not None and evening is not None:
                            is_night_astronomical = bool(morning.jd < evening.jd)
                            morning = morning.iso
                            evening = evening.iso
                        else:
                            morning = False
                            evening = False
                            is_night_astronomical = False
                    except Exception:
                        morning = False
                        evening = False
                        is_night_astronomical = False
                temp['is_night_astronomical'] = is_night_astronomical
                temp['next_twilight_morning_astronomical'] = morning
                temp['next_twilight_evening_astronomical'] = evening
                telescopes.append(temp)

            return self.success(data=telescopes)

    @permissions(['Manage sources'])
    def put(self, telescope_id):
        """
        ---
        description: Update telescope
        tags:
          - telescopes
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

        with self.Session() as session:
            t = session.scalars(
                Telescope.select(session.user_or_token, mode="update").where(
                    Telescope.id == int(telescope_id)
                )
            ).first()
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

            if 'name' in data:
                t.name = data['name']
            if 'nickname' in data:
                t.nickname = data['nickname']
            if 'elevation' in data:
                t.elevation = data['elevation']
            if 'lat' in data:
                t.lat = data['lat']
            if 'lon' in data:
                t.lon = data['lon']
            if 'diameter' in data:
                t.diameter = data['diameter']
            if 'robotic' in data:
                t.robotic = data['robotic']
            if 'fixed_location' in data:
                t.fixed_location = data['fixed_location']
            if 'skycam_link' in data:
                t.skycam_link = data['skycam_link']
            if 'weather_link' in data:
                t.weather_link = data['weather_link']

            session.commit()

            self.push_all(action="skyportal/REFRESH_TELESCOPES")
            return self.success()

    @permissions(['Manage sources'])
    def delete(self, telescope_id):
        """
        ---
        description: Delete a telescope
        tags:
          - telescopes
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

        with self.Session() as session:
            t = session.scalars(
                Telescope.select(session.user_or_token, mode="delete").where(
                    Telescope.id == int(telescope_id)
                )
            ).first()
            if t is None:
                return self.error('Invalid telescope ID.')
            session.delete(t)
            session.commit()
            self.push_all(action="skyportal/REFRESH_TELESCOPES")
            return self.success()
