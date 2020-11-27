from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    Listing,
)


class ListingHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
            description: get all objects corresponding to a specific user and that match a list name.
            parameters:
            - in: query
              name: user_id
              nullable: false
              schema:
                type: string
              description:
                return objects saved to list by this user.
            - in: query:
              name: list_name
              nullable: true
              schema:
                type: string
              description: |
                find all objects saved to this list.
                If empty, will return an array of strings
                specifying all non-empty lists associated with this user.
            responses:
              200:
                content:
                  schema:
                    allOf:
                      - $ref: '#/components/schemas/Success'
                      - type: array
                        items:
                          description: array of object ids or array of list names.
        """

        user_id = self.get_query_argument('user_id')
        list_name = self.get_query_argument('list_name', None)

        if list_name is None:
            lists = (
                DBSession().query(Listing).filter(Listing.user_id == user_id)
            ).unique()
            return self.success(data=lists)
        else:
            object_ids = (
                DBSession()
                .query(Listing)
                .filter(Listing.user_id == user_id)
                .filter(Listing.list_name == list_name)
            ).all()
            return self.success(data=object_ids)

    @auth_or_token
    def post(self):
        pass

    @auth_or_token
    def put(self):
        pass

    @auth_or_token
    def delete(self):
        pass
