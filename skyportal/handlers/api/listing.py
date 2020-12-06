import re

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    User,
    Obj,
    Listing,
)


class UserObjListHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
            description: get all objects corresponding to a specific user and that match a list name.
            parameters:
            - in: query
              name: user_id
              required: true
              type: string
            - in: query
              name: list_name
              required: false
              type: string

            description: |
                find all objects saved to this list.
                If not given will return all objects
                saved by the user to all lists.

            responses:
              200:
                content:
                  schema:
                    allOf:
                      - $ref: '#/components/schemas/Success'
                      - type: array
                        items:
                          description: array of listing objects
        """

        user_id = self.get_query_argument("user_id")

        if User.query.get(user_id) is None:  # verify that user exists
            return self.error(f'User "{user_id}" does not exist!')

        user_id = int(user_id)

        # verify that poster has read access to user_id's lists
        if (
            not self.associated_user_object.id == user_id
            and "System admin" not in self.associated_user_object.permissions
        ):
            return self.error('Insufficient permissions to access this listing. ')

        list_name = self.get_query_argument("list_name", None)

        objects = DBSession().query(Listing).filter(Listing.user_id == user_id)
        if list_name is not None and re.search(r'^\w+', list_name):
            objects = objects.filter(Listing.list_name == list_name)

        return self.success(data=objects.all())

    @auth_or_token
    def put(self):
        """
        ---
        description: Add a listing, if it doesn't exist yet
        parameters:
        - in: query
          name: user_id
          required: true
          type: string
        - in: query
          name: obj_id
          required: true
          type: string
        - in: query
          name: list_name
          required: true
          type: string
        description: |
            Listing name for this item, e.g., "favorites".
            Multiple objects can be saved by the same user to different
            lists, where the list names are user-defined.
            List name must be a non-empty string starting with an
            alphanumeric character or underscore.
            (it must match the regex: /^\\w+/)

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
                              description: New listing ID

        """

        user_id = self.get_query_argument("user_id")
        if User.query.get(user_id) is None:  # verify that user exists
            return self.error(f'User "{user_id}" does not exist!')

        user_id = int(user_id)
        print(user_id)
        print(self.associated_user_object.id)

        # verify that poster has write access to user_id's lists
        if (
            not self.associated_user_object.id == user_id
            and "System admin" not in self.associated_user_object.permissions
        ):
            return self.error('Insufficient permissions to access this listing. ')

        obj_id = self.get_query_argument("obj_id")
        if Obj.query.get(obj_id) is None:  # verify that object exists!
            return self.error(f'Object "{obj_id}" does not exist!')

        list_name = self.get_query_argument("list_name")
        if not re.search(r'^\w+', list_name):
            return self.error(
                "Input `list_name` must begin with alphanumeric/underscore"
            )

        print(obj_id)
        print(list_name)

        listing = Listing(user_id=user_id, obj_id=obj_id, list_name=list_name,)

        DBSession.add(listing)
        DBSession.commit()

        return self.success(data=listing.id)

    @auth_or_token
    def delete(self, listing_id):
        """
        ---
        description: Remove an existing listing
        parameters:
        - in: path
          name: listing_id
          required: true
          schema:
            type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success


        """

        listing = Listing.query.get(int(listing_id))

        if listing is None:
            return self.error("Listing does not exist.")

        # verify that poster has write access to user_id's lists
        if (
            not self.associated_user_object.id == listing.user_id
            and "System admin" not in self.associated_user_object.permissions
        ):
            return self.error('Insufficient permissions to access this listing. ')

        DBSession.delete(listing)
        DBSession.commit()

        return self.success()
