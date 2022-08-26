from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token

from ..base import BaseHandler
from ...models import Interferometer


class InterferometerHandler(BaseHandler):
    @permissions(['Manage allocations'])
    def post(self):
        """
        ---
        description: Create interferometer
        tags:
          - interferometers
        requestBody:
          content:
            application/json:
              schema: InterferometerNoID
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
                              description: New interferometer ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()

        with self.Session() as session:

            schema = Interferometer.__schema__()
            if 'lat' not in data or 'lon' not in data:
                return self.error('Missing latitude or longitude')
            elif not isinstance(data['lat'], (int, float)) or not isinstance(
                data['lon'], (int, float)
            ):
                return self.error('Latitude and longitude must all be numbers')
            elif (
                data['lat'] < -90
                or data['lat'] > 90
                or data['lon'] < -180
                or data['lon'] > 180
            ):
                return self.error(
                    'Latitude must be between -90 and 90, longitude between -180 and 180'
                )
            try:
                interferometer = schema.load(data)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )
            session.add(interferometer)
            session.commit()

            self.push_all(action="skyportal/REFRESH_INTERFEROMETERS")
            return self.success(data={"id": interferometer.id})

    @auth_or_token
    def get(self, interferometer_id=None):
        """
        ---
        single:
          description: Retrieve a interferometer
          tags:
            - interferometers
          parameters:
            - in: path
              name: interferometer_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleInterferometer
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all interferometers
          tags:
            - interferometers
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
                  schema: ArrayOfInterferometers
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:

            if interferometer_id is not None:
                t = session.scalars(
                    Interferometer.select(session.user_or_token).where(
                        Interferometer.id == int(interferometer_id)
                    )
                ).first()
                if t is None:
                    return self.error(
                        f"Could not load interferometer with ID {interferometer_id}"
                    )
                return self.success(data=t)

            tel_name = self.get_query_argument("name", None)
            stmt = Interferometer.select(session.user_or_token)
            if tel_name is not None:
                stmt = stmt.where(Interferometer.name == tel_name)

            data = session.scalars(stmt).all()
            return self.success(data=data)

    @permissions(['Manage allocations'])
    def put(self, interferometer_id):
        """
        ---
        description: Update interferometer
        tags:
          - interferometers
        parameters:
          - in: path
            name: interferometer_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: InterferometerNoID
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
                Interferometer.select(session.user_or_token, mode="update").where(
                    Interferometer.id == int(interferometer_id)
                )
            ).first()
            if t is None:
                return self.error('Invalid interferometer ID.')
            data = self.get_json()
            data['id'] = int(interferometer_id)

            schema = Interferometer.__schema__()
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
            if 'lat' in data:
                t.lat = data['lat']
            if 'lon' in data:
                t.lon = data['lon']

            session.commit()

            self.push_all(action="skyportal/REFRESH_INTERFEROMETERS")
            return self.success()

    @permissions(['Manage allocations'])
    def delete(self, interferometer_id):
        """
        ---
        description: Delete a interferometer
        tags:
          - interferometers
        parameters:
          - in: path
            name: interferometer_id
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
                Interferometer.select(session.user_or_token, mode="delete").where(
                    Interferometer.id == int(interferometer_id)
                )
            ).first()
            if t is None:
                return self.error('Invalid interferometer ID.')
            session.delete(t)
            session.commit()
            self.push_all(action="skyportal/REFRESH_INTERFEROMETERS")
            return self.success()
