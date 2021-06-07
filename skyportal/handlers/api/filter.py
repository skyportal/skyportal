from marshmallow.exceptions import ValidationError

from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import DBSession, Filter


class FilterHandler(BaseHandler):
    @auth_or_token
    def get(self, filter_id=None):
        """
        ---
        single:
          description: Retrieve a filter
          tags:
            - filters
          parameters:
            - in: path
              name: filter_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleFilter
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all filters
          tags:
            - filters
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfFilters
            400:
              content:
                application/json:
                  schema: Error
        """

        if filter_id is not None:
            f = Filter.get_if_accessible_by(
                filter_id,
                self.current_user,
                raise_if_none=True,
                options=[joinedload(Filter.stream)],
            )
            self.verify_and_commit()
            return self.success(data=f)

        filters = Filter.get_records_accessible_by(self.current_user)
        self.verify_and_commit()
        return self.success(data=filters)

    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: POST a new filter.
        tags:
          - filters
        requestBody:
          content:
            application/json:
              schema: FilterNoID
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
                              description: New filter ID
        """
        data = self.get_json()
        schema = Filter.__schema__()
        try:
            fil = schema.load(data)
        except ValidationError as e:
            return self.error(
                "Invalid/missing parameters: " f"{e.normalized_messages()}"
            )
        DBSession().add(fil)
        self.verify_and_commit()
        return self.success(data={"id": fil.id})

    @permissions(["Upload data"])
    def patch(self, filter_id):
        """
        ---
        description: Update filter name
        tags:
          - filters
        parameters:
          - in: path
            name: filter_id
            required: True
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: FilterNoID
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
        f = Filter.get_if_accessible_by(
            filter_id, self.current_user, mode="update", raise_if_none=True
        )
        data = self.get_json()
        data["id"] = filter_id

        schema = Filter.__schema__()
        try:
            fil = schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )

        if fil.group_id != f.group_id or fil.stream_id != f.stream_id:
            return self.error("Cannot update group_id or stream_id.")

        self.verify_and_commit()
        return self.success()

    @permissions(["Upload data"])
    def delete(self, filter_id):
        """
        ---
        description: Delete a filter
        tags:
          - filters
        parameters:
          - in: path
            name: filter_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        f = Filter.get_if_accessible_by(
            filter_id, self.current_user, mode="delete", raise_if_none=True
        )
        DBSession().delete(f)
        self.verify_and_commit()
        return self.success()
