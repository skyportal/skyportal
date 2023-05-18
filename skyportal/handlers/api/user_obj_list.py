import re
from marshmallow.exceptions import ValidationError

from baselayer.app.custom_exceptions import AccessError
from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
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
            schema:
              type: string
          - in: query
            name: listName
            required: false
            schema:
              type: string
            description: |
              name of the list to retrieve objects from.
              If not given will return all objects
              saved by the user to all lists.
        tags:
          - listings
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfListings
          400:
            content:
              application/json:
                schema: Error
        """

        if user_id is None:
            user_id = self.associated_user_object.id

        list_name = self.get_query_argument("listName", None)

        with self.Session() as session:
            stmt = Listing.select(self.current_user).where(Listing.user_id == user_id)

            if list_name is not None:
                stmt = stmt.where(Listing.list_name == list_name)

            listings = session.scalars(stmt).all()

            return self.success(data=listings)

    @auth_or_token
    def post(self):
        """
        ---
        description: Add a listing.
        tags:
        - listings
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
                  params:
                    type: object
                    required: false
                    description: |
                        Optional parameters for "watchlist" type listings, when searching for new candidates around a given object.
                        For example, if you want to search for new candidates around a given object, you can specify the search radius
                        and the number of candidates to return.
                        The parameters are passed to the microservice that is responsible for processing the listing.
                        The microservice will return a list of candidates that match the given parameters, and ingest them.

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

        if (
            user_id != self.associated_user_object.id
            and not self.associated_user_object.is_admin
        ):
            return self.error("Only admins can add listings to other users' accounts")

        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        obj_id = data.get('obj_id')
        obj_check = Obj.get(obj_id, self.current_user)
        if obj_check is None:
            return self.error(f'Cannot find Obj with ID: {obj_id}')

        list_name = data.get('list_name')
        if not check_list_name(list_name):
            return self.error(
                "Input `list_name` must begin with alphanumeric/underscore"
            )

        if list_name == "watchlist" and "params" not in data:
            return self.error("Input `params` must be provided for `watchlist`")

        params = data.get('params', None)

        if params is not None:
            if not isinstance(params, dict):
                return self.error("Input `params` must be a dictionary")
            if list_name == "watchlist":
                # verify that the params are "arcsec", "cadence", and "end_of_night"
                if "arcsec" not in params or "cadence" not in params:
                    return self.error(
                        "Input `params` must contain `arcsec` and `cadence`"
                    )
                if not isinstance(params["arcsec"], (int, float)) or not isinstance(
                    params["cadence"], (int, float)
                ):
                    return self.error(
                        "Inputs `params.arcsec` and `params.cadence` must be numbers"
                    )
                if (
                    params["arcsec"] <= 0
                    or params["cadence"] < 1
                    or params["arcsec"] > 3600
                ):
                    return self.error(
                        "Inputs `params.arcsec` must be higher than 0 and less than 3600, and `params.cadence` must be 1 and above"
                    )
                if "end_of_night" in params and not isinstance(
                    params["end_of_night"], bool
                ):
                    return self.error("Input `params.end_of_night` must be a boolean")

        with self.Session() as session:
            stmt = Listing.select(self.current_user).where(
                Listing.user_id == user_id,
                Listing.list_name == list_name,
                Listing.obj_id == obj_id,
            )

            # what to do if listing already exists...
            if session.scalars(stmt).first() is not None:
                return self.error(
                    f'Listing already exists with user_id={user_id}, '
                    f'obj_id={obj_id} and list_name={list_name}'
                )

            listing = Listing(
                user_id=user_id, obj_id=obj_id, list_name=list_name, params=params
            )

            session.add(listing)

            try:
                session.commit()
            except AccessError as e:
                return self.error(str(e))

            if list_name == "favorites":
                self.push(action='skyportal/REFRESH_FAVORITES')
                self.push(action='skyportal/REFRESH_FAVORITE_SOURCES')
            if list_name == "rejected_candidates":
                self.push(action='skyportal/REFRESH_REJECTED_CANDIDATES')

            return self.success(data={'id': listing.id})

    @auth_or_token
    def patch(self, listing_id):
        """
        ---
        description: Update an existing listing
        tags:
        - listings
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
        with self.Session() as session:
            listing = session.scalars(
                Listing.select(self.current_user, mode="update").where(
                    Listing.id == listing_id
                )
            ).first()
            if listing is None:
                return self.error(f'Cannot find listing with ID: {listing_id}')

            # get the data from the request body
            data = self.get_json()

            schema = Listing.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    f'Invalid/missing parameters: {e.normalized_messages()}'
                )

            user_id = data.get('user_id', listing.user_id)
            user_id = int(user_id)
            if (
                user_id != self.associated_user_object.id
                and not self.current_user.is_system_admin
            ):
                return self.error("Insufficient permissions.")

            obj_id = data.get('obj_id', listing.obj_id)
            obj_check = session.scalars(
                Obj.select(self.current_user).where(Obj.id == obj_id)
            ).first()
            if obj_check is None:
                return self.error(f'Cannot find Obj with ID: {obj_id}')

            list_name = data.get('list_name', listing.list_name)

            if not check_list_name(list_name):
                return self.error(
                    "Input `list_name` must begin with alphanumeric/underscore"
                )

            listing.user_id = user_id
            listing.obj_id = obj_id
            listing.list_name = list_name

            session.commit()

            if list_name == "favorites":
                self.push(action='skyportal/REFRESH_FAVORITES')
                self.push(action='skyportal/REFRESH_FAVORITE_SOURCES')
            if list_name == "rejected_candidates":
                self.push(action='skyportal/REFRESH_REJECTED_CANDIDATES')

            return self.success()

    @auth_or_token
    def delete(self, listing_id=None):
        """
        ---
        description: Remove an existing listing
        tags:
        - listings
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
        with self.Session() as session:
            if listing_id is not None:
                try:
                    listing_id = int(listing_id)
                except ValueError:
                    return self.error(f"Invalid listing_id {listing_id}")

                listing = session.scalars(
                    Listing.select(self.current_user).where(Listing.id == listing_id)
                ).first()
                if listing is None:
                    return self.error(f'Cannot find listing with ID: {listing_id}')
            else:
                data = self.get_json()

                schema = Listing.__schema__(exclude=['user_id'])
                user_id = data.pop('user_id', self.associated_user_object.id)

                try:
                    schema.load(data)
                except ValidationError as e:
                    return self.error(
                        f'Invalid/missing parameters: {e.normalized_messages()}'
                    )

                obj_id = data.get('obj_id')
                obj_test = session.scalars(
                    Obj.select(self.current_user).where(Obj.id == obj_id)
                ).first()
                if obj_test is None:
                    return self.error(f'Cannot find Obj with ID: {obj_id}')

                list_name = data.get('list_name')
                listing = session.scalars(
                    Listing.select(self.current_user, mode="delete").where(
                        Listing.user_id == user_id,
                        Listing.obj_id == obj_id,
                        Listing.list_name == list_name,
                    )
                ).first()

            if listing is None:
                return self.error("Cannot delete Listing.")

            list_name = listing.list_name

            session.delete(listing)
            session.commit()

            if list_name == "favorites":
                self.push(action='skyportal/REFRESH_FAVORITES')
                self.push(action='skyportal/REFRESH_FAVORITE_SOURCES')
            if list_name == "rejected_candidates":
                self.push(action='skyportal/REFRESH_REJECTED_CANDIDATES')

            return self.success()
