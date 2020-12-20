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
    def get(self, user_id=None):
        """
        ---
        description: get all listings corresponding to a specific user and that match a list name.
        parameters:
        - in: path
          name: user_id
          required: false
          type: string
        - in: query
          name: listName
          required: false
          type: string
          description: |
            name of the list to retrieve objects from.
            If not given will return all objects
            saved by the user to all lists.
        responses:
          200:
            content:
              schema: ArrayOfListings
        """

        if user_id is None:
            user_id = self.current_user

        if User.query.get(user_id) is None:  # verify that user exists
            return self.error(f'User "{user_id}" does not exist!')

        try:
            user_id = int(user_id)
        except ValueError:
            return self.error("Invalid `user_id` parameter; unable to parse to integer")

        # verify that poster has read access to user_id's lists
        if (
            self.associated_user_object.id != user_id
            and "System admin" not in self.associated_user_object.permissions
        ):
            return self.error('Insufficient permissions to access this listing. ')

        list_name = self.get_query_argument("listName", None)

        query = DBSession().query(Listing).filter(Listing.user_id == user_id)

        if list_name is not None:
            query = query.filter(Listing.list_name == list_name)

        return self.success(data=query.all())

    def add_listing(self, error_if_exists):
        """
        Add the listing given in the request body.
        error_if_exists: boolean
          true: will throw an error if listing exists (POST)
          false: will ignore if listing already exists (PUT)
        """

        data = self.get_json()

        schema = Listing.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        user_id = int(data.get('user_id'))

        if User.query.get(user_id) is None:  # verify that user exists
            return self.error(f'User "{user_id}" does not exist!')

        # verify that poster has write access to user_id's lists
        if (
            not self.associated_user_object.id == user_id
            and "System admin" not in self.associated_user_object.permissions
        ):
            return self.error('Insufficient permissions to access this listing. ')

        obj_id = data.get('obj_id')
        if Obj.query.get(obj_id) is None:  # verify that object exists!
            return self.error(f'Object "{obj_id}" does not exist!')

        list_name = data.get('list_name')
        if not re.search(r'^\w+', list_name):
            return self.error(
                "Input `list_name` must begin with alphanumeric/underscore"
            )

        query = (
            DBSession()
            .query(Listing)
            .filter(
                Listing.user_id == user_id,
                Listing.obj_id == obj_id,
                Listing.list_name == list_name,
            )
        )

        # what to do if listing already exists...
        if query.first() is not None:
            if error_if_exists:
                return self.error(
                    f'Listing already exists with user_id={user_id}, obj_id={obj_id} and list_name={list_name}'
                )
            else:  # if user, obj and list name are identical, no need for an update of existing record
                return self.success(data={'listing_id': query.first().id})

        # no such listing, can just add a new one!
        listing = Listing(user_id=user_id, obj_id=obj_id, list_name=list_name)

        DBSession().add(listing)
        DBSession().commit()

        return self.success(data={'listing_id': listing.id})

    @auth_or_token
    def post(self):
        """
        ---
        description: Add a listing.
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: integer
                    required: true
                  obj_id:
                    type: string
                    required: true
                  list_name:
                    type: string
                    required: true
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
                            listing_id:
                              type: integer
                              description: New listing ID

        """

        return self.add_listing(error_if_exists=True)

    @auth_or_token
    def put(self):
        """
        ---
        description: Add a listing, if it exists, ignore this call
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: integer
                    required: true
                  obj_id:
                    type: string
                    required: true
                  list_name:
                    type: string
                    required: true
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
                            listing_id:
                              type: integer
                              description: New or existing listing ID

        """

        return self.add_listing(error_if_exists=False)

    @auth_or_token
    def patch(self, listing_id):
        """
        ---
        description: Update an existing listing
        parameters:
        - in: path
          name: listing_id
          required: true
          schema:
            type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: integer
                    required: true
                  obj_id:
                    type: string
                    required: true
                  list_name:
                    type: string
                    required: true
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
                schema: Success

        """

        try:
            listing = Listing.query.get(int(listing_id))
        except TypeError:
            return self.error('Listing ID must be convertible to int. ')

        if listing is None:
            return self.error("Listing does not exist.")

        # verify that poster has write access to user_id's lists
        if (
            self.associated_user_object.id != listing.user_id
            and "System admin" not in self.associated_user_object.permissions
        ):
            return self.error('Insufficient permissions to access this listing. ')

        # get the data from the request body
        data = self.get_json()

        schema = Listing.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        user_id = int(data.get('user_id'))

        if User.query.get(user_id) is None:  # verify that user exists
            return self.error(f'User "{user_id}" does not exist!')

        # verify that poster has write access to the new user_id
        if (
            self.associated_user_object.id != user_id
            and "System admin" not in self.associated_user_object.permissions
        ):
            return self.error(
                f'Insufficient permissions to change listings for user ID: {user_id}. '
            )

        obj_id = data.get('obj_id')
        if Obj.query.get(obj_id) is None:  # verify that object exists!
            return self.error(f'Object "{obj_id}" does not exist!')

        list_name = data.get('list_name')
        if not re.search(r'^\w+', list_name):
            return self.error(
                "Input `list_name` must begin with alphanumeric/underscore"
            )

        listing.user_id = user_id
        listing.obj_id = obj_id
        listing.list_name = list_name

        DBSession().commit()

        return self.success()

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
            self.associated_user_object.id != listing.user_id
            and "System admin" not in self.associated_user_object.permissions
        ):
            return self.error('Insufficient permissions to access this listing. ')

        DBSession.delete(listing)
        DBSession.commit()

        return self.success()
