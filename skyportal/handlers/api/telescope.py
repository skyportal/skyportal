from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token

from ..base import BaseHandler
from ...models import DBSession, Telescope


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

        schema = Telescope.__schema__()
        # check if the telescope has a fixed location
        if 'fixed_location' in data:
            if data['fixed_location']:
                if 'lat' not in data or 'lon' not in data or 'elevation' not in data:
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
        DBSession().add(telescope)
        self.verify_and_commit()

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
        if telescope_id is not None:
            t = Telescope.query.get(int(telescope_id))
            if t is None:
                return self.error(f"Could not load telescope with ID {telescope_id}")
            self.verify_and_commit()
            return self.success(data=t)
        tel_name = self.get_query_argument("name", None)
        query = Telescope.query
        if tel_name is not None:
            query = query.filter(Telescope.name == tel_name)

        data = query.all()
        telescopes = []
        for telescope in data:
            temp = telescope.to_dict()
            if telescope.next_twilight_morning_astronomical() is not None:
                temp['is_night_astronomical'] = bool(
                    telescope.next_twilight_morning_astronomical().jd
                    < telescope.next_twilight_evening_astronomical().jd
                )
                temp[
                    'next_twilight_morning_astronomical'
                ] = telescope.next_twilight_morning_astronomical().iso
                temp[
                    'next_twilight_evening_astronomical'
                ] = telescope.next_twilight_evening_astronomical().iso
            else:
                temp['is_night_astronomical'] = False
                temp['next_twilight_morning_astronomical'] = False
                temp['next_twilight_evening_astronomical'] = False

            telescopes.append(temp)
        self.verify_and_commit()
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
        self.verify_and_commit()

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
        t = Telescope.query.get(int(telescope_id))
        if t is None:
            return self.error('Invalid telescope ID.')

        DBSession().query(Telescope).filter(Telescope.id == int(telescope_id)).delete()
        self.verify_and_commit()

        self.push_all(action="skyportal/REFRESH_TELESCOPES")
        return self.success()
