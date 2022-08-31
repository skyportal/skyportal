from sqlalchemy.orm import joinedload

from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token

from ..base import BaseHandler
from ...models import MMADetector


class MMADetectorHandler(BaseHandler):
    @permissions(['Manage allocations'])
    def post(self):
        """
        ---
        description: Create mmadetector
        tags:
          - mmadetectors
        requestBody:
          content:
            application/json:
              schema: MMADetectorNoID
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
                              description: New mmadetector ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()

        with self.Session() as session:

            schema = MMADetector.__schema__()
            try:
                mmadetector = schema.load(data)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )
            if data['fixed_location']:
                if (
                    data['lat'] < -90
                    or data['lat'] > 90
                    or data['lon'] < -180
                    or data['lon'] > 180
                ):
                    return self.error(
                        'Latitude must be between -90 and 90, longitude between -180 and 180'
                    )
            session.add(mmadetector)
            session.commit()

            self.push_all(action="skyportal/REFRESH_MMADETECTORS")
            return self.success(data={"id": mmadetector.id})

    @auth_or_token
    def get(self, mmadetector_id=None):
        """
        ---
        single:
          description: Retrieve a mmadetector
          tags:
            - mmadetectors
          parameters:
            - in: path
              name: mmadetector_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleMMADetector
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all mmadetectors
          tags:
            - mmadetectors
          parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by name
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfMMADetectors
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:

            if mmadetector_id is not None:
                t = session.scalars(
                    MMADetector.select(
                        session.user_or_token, options=[joinedload(MMADetector.events)]
                    ).where(MMADetector.id == int(mmadetector_id))
                ).first()
                if t is None:
                    return self.error(
                        f"Could not load MMA Detector with ID {mmadetector_id}"
                    )
                return self.success(data=t)

            det_name = self.get_query_argument("name", None)
            stmt = MMADetector.select(session.user_or_token)
            if det_name is not None:
                stmt = stmt.where(MMADetector.name.contains(det_name))

            data = session.scalars(stmt).all()
            return self.success(data=data)

    @permissions(['Manage allocations'])
    def patch(self, mmadetector_id):
        """
        ---
        description: Update mmadetector
        tags:
          - mmadetectors
        parameters:
          - in: path
            name: mmadetector_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: MMADetectorNoID
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
                MMADetector.select(session.user_or_token, mode="update").where(
                    MMADetector.id == int(mmadetector_id)
                )
            ).first()
            if t is None:
                return self.error('Invalid MMA Detector ID.')
            data = self.get_json()
            data['id'] = int(mmadetector_id)

            schema = MMADetector.__schema__()
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
                if data['lat'] < -90 or data['lat'] > 90:
                    return self.error('Latitude must be between -90 and 90')
                t.lat = data['lat']
            if 'lon' in data:
                if data['lon'] < -180 or data['lon'] > 180:
                    return self.error('Longitude between -180 and 180')
                t.lon = data['lon']
            if 'fixed_location' in data:
                t.fixed_location = data['fixed_location']
            if 'type' in data:
                t.type = data['type']

            session.commit()

            self.push_all(action="skyportal/REFRESH_MMADETECTORS")
            return self.success()

    @permissions(['Manage allocations'])
    def delete(self, mmadetector_id):
        """
        ---
        description: Delete a mmadetector
        tags:
          - mmadetectors
        parameters:
          - in: path
            name: mmadetector_id
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
                MMADetector.select(session.user_or_token, mode="delete").where(
                    MMADetector.id == int(mmadetector_id)
                )
            ).first()
            if t is None:
                return self.error('Invalid MMA Detector ID.')
            session.delete(t)
            session.commit()
            self.push_all(action="skyportal/REFRESH_MMADETECTORS")
            return self.success()
