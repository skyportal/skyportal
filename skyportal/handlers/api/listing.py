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


class ListingHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
            description: get all objects corresponding to a specific user and that match a list name.
            requestBody:
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      user_id:
                        type: string
                      list_name:
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
        data = self.get_json()

        schema = Listing.__schema__(exclude=["obj_id"])
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        # should we make user_id optional, defaulting to self.associated_user_object?
        user_id = data.get("user_id")
        if User.query.get(user_id) is None:  # verify that user exists
            return self.error(f'User "{user_id}" does not exist!')

        # verify that poster has read access to user_id's lists?

        list_name = data.get("list_name")

        if list_name is None:
            listings = (
                DBSession().query(Listing).filter(Listing.user_id == user_id)
            ).all()

            list_names = [L.list_name for L in listings]
            list_names = list(set(list_names))  # show only unique list names

            return self.success(data=list_names)

        else:
            listings = (
                DBSession()
                .query(Listing)
                .filter(Listing.user_id == user_id)
                .filter(Listing.list_name == list_name)
            ).all()

            object_ids = [L.obj_id for L in listings]

            return self.success(data=object_ids)

    @auth_or_token
    def put(self):
        """
        ---
        description: Add a listing, if it doesn't exist yet
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: string
                  obj_id:
                    type: string
                  list_name:
                     type: string
                     description: |
                        Listing name for this item, e.g., "favorites".
                        Multiple objects can be saved by the same user to different
                        lists, where the list names are user-defined.
                        List name must be a non-empty string starting with an
                        alphanumeric character or underscore.
                        (it must match the regex: /^\\w+/)


                required:
                  - user_id
                  - obj_id
                  - list_name

                """
        data = self.get_json()

        schema = Listing.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        # should we make user_id optional, defaulting to self.associated_user_object?
        user_id = data.get("user_id")
        if User.query.get(user_id) is None:  # verify that user exists
            return self.error(f'User "{user_id}" does not exist!')

        # verify that poster has write access to user_id's lists?

        obj_id = data.get("obj_id")
        if Obj.query.get(obj_id) is None:  # verify that object exists!
            return self.error(f'Object "{obj_id}" does not exist!')

        list_name = data.get("list_name")
        if not re.search(r'^\w+', list_name):
            return self.error(
                "Input `list_name` must begin with alphanumeric/underscore"
            )

        listing = Listing(user_id=user_id, obj_id=obj_id, list_name=list_name,)

        DBSession.add(listing)
        DBSession.commit()

        return self.success(data={})  # should we return something?

    @auth_or_token
    def delete(self):
        """
                ---
                description: Remove an existing listing
                requestBody:
                  content:
                    application/json:
                      schema:
                        type: object
                        properties:
                          user_id:
                            type: string
                          obj_id:
                            type: string
                          list_name:
                             type: string
                             description: |
                                Listing name for this item, e.g., "favorites".

                        required:
                          - user_id
                          - obj_id
                          - list_name

                        """
        data = self.get_json()

        schema = Listing.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        # should we make user_id optional, defaulting to self.associated_user_object?
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
