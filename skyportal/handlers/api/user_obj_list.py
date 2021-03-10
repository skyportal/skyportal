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


def check_list_name(name):
    """checks that list_name begins with an alphanumeric character

    Parameters
    ----------
    name: string
          name of the new listing.

    Return
    ------
    bool
        True if listing name conforms to requirements

    """
    return re.search(r'^\w+', name) is not None


def check_user_and_permissions(user_id, associated_user):
    """Verify that the user id is valid, and that the user has access to the requested user's listings.

    Parameters
    ----------
    user_id: integer
            the ID of the user associated witht the listing, not necessarily the poster.
    associated_user: integer
            the ID of the user that is posting the listing.

    Return
    ------
    bool
        If fails, return an error string. If succeeds, return None.

    """

    try:
        user_id = int(user_id)
    except ValueError:
        return "Invalid `user_id` parameter; unable to parse to integer"

    if User.query.get(user_id) is None:  # verify that user exists
        return f'User "{user_id}" does not exist!'

    # verify that poster has write access to user_id's lists
    if (
        associated_user.id != user_id
        and "System admin" not in associated_user.permissions
    ):
        return 'Insufficient permissions to access this listing.'

    return None


class UserObjListHandler(BaseHandler):
    @auth_or_token
    def get(self, user_id=None):
        """
        ---
        description: Retrieve sources from a user's lists
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
            user_id = self.associated_user_object.id

        error_obj = check_user_and_permissions(user_id, self.associated_user_object)
        if error_obj is not None:
            return self.error(error_obj)

        list_name = self.get_query_argument("listName", None)

        query = DBSession().query(Listing).filter(Listing.user_id == user_id)

        if list_name is not None:
            query = query.filter(Listing.list_name == list_name)

        return self.success(data=query.all())

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
                    required: false
                    description: |
                      ID of user that you want to add the listing to.
                      If not given, will default to the associated user object that is posting.
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
                            id:
                              type: integer
                              description: New listing ID

        """

        data = self.get_json()

        schema = Listing.__schema__(exclude=['user_id'])
        user_id = data.pop('user_id', None)

        if user_id is None:
            user_id = self.associated_user_object.id

        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        err_str = check_user_and_permissions(user_id, self.associated_user_object)
        if err_str is not None:
            return self.error(err_str)

        obj_id = data.get('obj_id')
        if Obj.query.get(obj_id) is None:  # verify that object exists!
            return self.error(f'Object "{obj_id}" does not exist!')

        list_name = data.get('list_name')
        if not check_list_name(list_name):
            return self.error(
                "Input `list_name` must begin with alphanumeric/underscore"
            )

        query = (
            DBSession()
            .query(Listing)
            .filter(
                Listing.user_id == int(user_id),
                Listing.obj_id == obj_id,
                Listing.list_name == list_name,
            )
        )

        # what to do if listing already exists...
        if query.first() is not None:
            return self.error(
                f'Listing already exists with user_id={user_id}, obj_id={obj_id} and list_name={list_name}'
            )

        listing = Listing(user_id=user_id, obj_id=obj_id, list_name=list_name)
        DBSession().add(listing)
        DBSession().commit()

        self.push(action='skyportal/REFRESH_FAVORITES')
        self.push(action='skyportal/REFRESH_FAVORITE_SOURCES')
        self.push(action='skyportal/REFRESH_REJECTED_CANDIDATES')

        return self.success(data={'id': listing.id})

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

        err_str = check_user_and_permissions(
            listing.user_id, self.associated_user_object
        )
        if err_str is not None:
            return self.error(err_str)

        # get the data from the request body
        data = self.get_json()

        schema = Listing.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        user_id = data.get('user_id', listing.user_id)
        user_id = int(user_id)

        err_str = check_user_and_permissions(user_id, self.associated_user_object)
        if err_str is not None:
            return self.error(err_str)

        obj_id = data.get('obj_id', listing.obj_id)
        if Obj.query.get(obj_id) is None:  # verify that object exists!
            return self.error(f'Object "{obj_id}" does not exist!')

        list_name = data.get('list_name', listing.list_name)

        if not check_list_name(list_name):
            return self.error(
                "Input `list_name` must begin with alphanumeric/underscore"
            )

        listing.user_id = user_id
        listing.obj_id = obj_id
        listing.list_name = list_name

        DBSession().commit()

        self.push(action='skyportal/REFRESH_FAVORITES')
        self.push(action='skyportal/REFRESH_FAVORITE_SOURCES')
        self.push(action='skyportal/REFRESH_REJECTED_CANDIDATES')

        return self.success()

    @auth_or_token
    def delete(self, listing_id=None):
        """
        ---
        description: Remove an existing listing
        parameters:
        - in: path
          name: listing_id
          required: false
          description: |
            ID of the listing object. If not given, must supply
            the listing's obj_id and list_name (and user_id)
            to find the correct listing id from that info.
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
                    required: false
                    description: |
                      ID of user that you want to add the listing to.
                      If not given, will default to the associated user object that is posting.
                  obj_id:
                    type: string
                    required: true
                  list_name:
                    type: string
                    required: true
                    description: |
                        Listing name for this item, e.g., "favorites".
        responses:
          200:
            content:
              application/json:
                schema: Success


        """

        if listing_id is not None:
            listing = Listing.query.get(int(listing_id))
        else:
            data = self.get_json()

            schema = Listing.__schema__(exclude=['user_id'])
            user_id = data.pop('user_id', None)

            if user_id is None:
                user_id = self.associated_user_object.id

            try:
                schema.load(data)
            except ValidationError as e:
                return self.error(
                    f'Invalid/missing parameters: {e.normalized_messages()}'
                )

            obj_id = data.get('obj_id')
            if Obj.query.get(obj_id) is None:  # verify that object exists!
                return self.error(f'Object "{obj_id}" does not exist!')

            list_name = data.get('list_name')
            listing = Listing.query.filter(
                Listing.user_id == user_id,
                Listing.obj_id == obj_id,
                Listing.list_name == list_name,
            ).first()

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

        self.push(action='skyportal/REFRESH_FAVORITES')
        self.push(action='skyportal/REFRESH_FAVORITE_SOURCES')
        self.push(action='skyportal/REFRESH_REJECTED_CANDIDATES')

        return self.success()
