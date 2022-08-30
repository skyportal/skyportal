from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token

from ..base import BaseHandler
from ...models import GWDetector


class GWDetectorHandler(BaseHandler):
    @permissions(['Manage allocations'])
    def post(self):
        """
        ---
        description: Create gwdetector
        tags:
          - gwdetectors
        requestBody:
          content:
            application/json:
              schema: GWDetectorNoID
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
                              description: New gwdetector ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()

        with self.Session() as session:

            schema = GWDetector.__schema__()
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
                gwdetector = schema.load(data)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )
            session.add(gwdetector)
            session.commit()

            self.push_all(action="skyportal/REFRESH_GWDETECTORS")
            return self.success(data={"id": gwdetector.id})

    @auth_or_token
    def get(self, gwdetector_id=None):
        """
        ---
        single:
          description: Retrieve a gwdetector
          tags:
            - gwdetectors
          parameters:
            - in: path
              name: gwdetector_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleGWDetector
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all gwdetectors
          tags:
            - gwdetectors
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
                  schema: ArrayOfGWDetectors
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:

            if gwdetector_id is not None:
                t = session.scalars(
                    GWDetector.select(session.user_or_token).where(
                        GWDetector.id == int(gwdetector_id)
                    )
                ).first()
                if t is None:
                    return self.error(
                        f"Could not load GW Detector with ID {gwdetector_id}"
                    )
                return self.success(data=t)

            tel_name = self.get_query_argument("name", None)
            stmt = GWDetector.select(session.user_or_token)
            if tel_name is not None:
                stmt = stmt.where(GWDetector.name == tel_name)

            data = session.scalars(stmt).all()
            return self.success(data=data)

    @permissions(['Manage allocations'])
    def put(self, gwdetector_id):
        """
        ---
        description: Update gwdetector
        tags:
          - gwdetectors
        parameters:
          - in: path
            name: gwdetector_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: GWDetectorNoID
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
                GWDetector.select(session.user_or_token, mode="update").where(
                    GWDetector.id == int(gwdetector_id)
                )
            ).first()
            if t is None:
                return self.error('Invalid GW Detector ID.')
            data = self.get_json()
            data['id'] = int(gwdetector_id)

            schema = GWDetector.__schema__()
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

            self.push_all(action="skyportal/REFRESH_GWDETECTORS")
            return self.success()

    @permissions(['Manage allocations'])
    def delete(self, gwdetector_id):
        """
        ---
        description: Delete a gwdetector
        tags:
          - gwdetectors
        parameters:
          - in: path
            name: gwdetector_id
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
                GWDetector.select(session.user_or_token, mode="delete").where(
                    GWDetector.id == int(gwdetector_id)
                )
            ).first()
            if t is None:
                return self.error('Invalid GW Detector ID.')
            session.delete(t)
            session.commit()
            self.push_all(action="skyportal/REFRESH_GWDETECTORS")
            return self.success()
