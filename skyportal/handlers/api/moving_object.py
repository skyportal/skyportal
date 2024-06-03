import sqlalchemy as sa
from marshmallow.exceptions import ValidationError
from sqlalchemy import func

from baselayer.app.access import auth_or_token, permissions

from ...models import (
    MovingObject,
)
from ..base import BaseHandler

MAX_MOVING_OBJECTS = 1000


class MovingObjectHandler(BaseHandler):
    @auth_or_token
    def get(self, moving_object_id=None):
        """
        ---
        single:
          tags:
            - moving_objects
          description: Retrieve a moving object
          parameters:
            - in: path
              name: moving_object_id
              required: true
              schema:
                type: integer
          responses:
            200:
               content:
                application/json:
                  schema: SingleMovingObject
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          tags:
            - moving_objects
          description: Retrieve all moving objects
          parameters:
          - in: query
            name: obj_id
            nullable: true
            schema:
              type: number
            description: Retrieve moving objects associated with list of obj_id.
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of moving objects to return per paginated request. Defaults to 10. Can be no larger than {MAX_MOVING_OBJECTS}.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for paginated query results. Defaults to 1.
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfMovingObjects
            400:
              content:
                application/json:
                  schema: Error
        """

        # get owned moving objects

        with self.Session() as session:
            moving_objects = MovingObject.select(session.user_or_token)

            if moving_object_id is not None:
                try:
                    moving_object_id = int(moving_object_id)
                except ValueError:
                    return self.error("MovingObject ID must be an integer.")

                moving_object = MovingObject.select(session.user_or_token).where(
                    MovingObject.id == moving_object_id
                )
                moving_object = session.scalars(moving_object).first()
                if moving_object is None:
                    return self.error("Could not retrieve moving object.")

                table = moving_object.table.to_pandas().to_dict('records')
                moving_object = {**moving_object.to_dict(), 'table': table}

                return self.success(data=moving_object)

            moving_objects = MovingObject.select(session.user_or_token)

            page_number = self.get_query_argument("pageNumber", 1)
            n_per_page = self.get_query_argument("numPerPage", 10)
            obj_id = self.get_query_argument("obj_id", None)

            if obj_id is not None:
                moving_objects = moving_objects.where(
                    MovingObject.obj_ids.contains([obj_id.strip()])
                )

            try:
                page_number = int(page_number)
            except ValueError:
                return self.error("Invalid page number value.")

            try:
                n_per_page = int(n_per_page)
            except (ValueError, TypeError) as e:
                return self.error(f"Invalid numPerPage value: {str(e)}")

            if n_per_page > MAX_MOVING_OBJECTS:
                return self.error(
                    f'numPerPage should be no larger than {MAX_MOVING_OBJECTS}.'
                )

            count_stmt = sa.select(func.count()).select_from(moving_objects)
            total_matches = session.execute(count_stmt).scalar()

            if n_per_page is not None:
                moving_objects = (
                    moving_objects.distinct()
                    .limit(n_per_page)
                    .offset((page_number - 1) * n_per_page)
                )

            moving_objects = session.scalars(moving_objects).unique().all()
            return self.success(
                data={
                    'moving_objects': moving_objects,
                    "totalMatches": int(total_matches),
                }
            )

    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Post new moving object
        tags:
          - moving_objects
        requestBody:
          content:
            application/json:
              schema: MovingObjectNoID
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
                              description: New moving object ID
        """

        data = self.get_json()
        with self.Session() as session:
            try:
                moving_object = MovingObject.__schema__().load(data=data)
            except ValidationError as e:
                return self.error(
                    f'Error parsing posted moving_object: "{e.normalized_messages()}"'
                )

            session.add(moving_object)
            session.commit()
            return self.success(data={"id": moving_object.id})

    @permissions(['Upload data'])
    def put(self, moving_object_id):
        """
        ---
        description: Update a moving object
        tags:
          - moving_objects
        parameters:
          - in: path
            name: moving_object_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: MovingObjectNoID
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
            moving_object = session.scalars(
                MovingObject.select(session.user_or_token, mode="update").where(
                    MovingObject.id == int(moving_object_id)
                )
            ).first()
            if moving_object is None:
                return self.error('No such moving_object')

            data = self.get_json()
            data['id'] = moving_object_id

            schema = MovingObject.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )

            for k in data:
                setattr(moving_object, k, data[k])

            session.commit()
            return self.success()

    @permissions(['Upload data'])
    def delete(self, moving_object_id):
        """
        ---
        description: Delete a moving object.
        tags:
          - moving_objects
        parameters:
          - in: path
            name: moving_object_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            moving_object = session.scalars(
                MovingObject.select(session.user_or_token, mode="delete").where(
                    MovingObject.id == int(moving_object_id)
                )
            ).first()
            if moving_object is None:
                return self.error('No such moving_object')

            session.delete(moving_object)
            session.commit()
            return self.success()
