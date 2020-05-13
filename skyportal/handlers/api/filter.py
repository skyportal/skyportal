from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    Filter,
)


class FilterHandler(BaseHandler):
    @auth_or_token
    def get(self, filter_id=None):
        """
        ---
        single:
          description: Retrieve a filter
          parameters:
            - in: path
              name: filter_id
              required: false
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
            f = Filter.get_if_owned_by(filter_id, self.current_user)
            if f is None:
                return self.error("Invalid filter ID.")
            return self.success(data={"filters": f})
        filters = (
            DBSession.query(Filter)
            .filter(Filter.group_id.in_([g.id for g in self.current_user.groups]))
            .all()
        )
        return self.success(data={"filters": filters})

    @permissions(["Manage groups"])
    def post(self):
        """
        ---
        description: POST a new filter.
        requestBody:
          content:
            application/json:
              schema: Filter
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        id:
                          type: string
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
        DBSession.add(fil)
        DBSession().commit()

        return self.success(data={"id": fil.id})
