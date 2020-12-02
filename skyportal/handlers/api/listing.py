import re
from marshmallow.exceptions import ValidationError
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
                          description: array of object ids.
        """

        user_id = self.get_query_argument("user_id")

        if User.query.get(user_id) is None:  # verify that user exists
            return self.error(f'User "{user_id}" does not exist!')

        # verify that poster has read access to user_id's lists?

        list_name = self.get_query_argument("list_name", None)

        objects = DBSession().query(Listing).filter(Listing.user_id == user_id)
        if list_name is not None:
            objects = objects.filter(Listing.list_name == list_name)

        obj_ids = [obj.obj_id for obj in objects.all()]
        obj_ids = list(set(obj_ids))  # choose only the unique obj_ids

        return self.success(data=obj_ids)

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

        # should we make user_id optional, defaulting to self.associated_user_object?
        user_id = self.get_query_argument("user_id")
        if User.query.get(user_id) is None:  # verify that user exists
            return self.error(f'User "{user_id}" does not exist!')

        # verify that poster has write access to user_id's lists?

        obj_id = self.get_query_argument("obj_id")
        if Obj.query.get(obj_id) is None:  # verify that object exists!
            return self.error(f'Object "{obj_id}" does not exist!')

        list_name = self.get_query_argument("list_name")
        if not re.search(r'^\w+', list_name):
            return self.error(
                "Input `list_name` must begin with alphanumeric/underscore"
            )

        listing = Listing(user_id=user_id, obj_id=obj_id, list_name=list_name,)

        DBSession.add(listing)
        DBSession.commit()

        return self.success(data={listing.id})

    @auth_or_token
    def delete(self):
        """
        ---
        description: Remove an existing listing
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

        """
        data = self.get_json()

        schema = Listing.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        user_id = data.get("user_id")
        if User.query.get(user_id) is None:  # verify that user exists
            return self.error(f'User "{user_id}" does not exist!')

        # verify that poster has write access to user_id's lists?

        obj_id = data.get("obj_id")
        list_name = data.get("list_name")

        q = Listing.query.filter_by(
            user_id=user_id, obj_id=obj_id, list_name=list_name
        ).first()
        if q is None:
            return self.error("Listing does not exist.")

        q.delete()
        DBSession.commit()

        return self.success(data={})  # should we return something?
