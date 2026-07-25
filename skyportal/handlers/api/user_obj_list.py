import re
from typing import Any

from marshmallow.exceptions import ValidationError
from pydantic import BaseModel, ConfigDict, Field

from baselayer.app.access import auth_or_token
from baselayer.app.custom_exceptions import AccessError

from ...models import (
    Listing,
    Obj,
)
from ..base import BaseHandler


class ListingPostBody(BaseModel):
    """Request body for adding a listing."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str = Field(description="ID of the object to add to the list.")
    list_name: str = Field(
        description='Listing name for this item, e.g., "favorites". '
        "Multiple objects can be saved by the same user to different "
        "lists, where the list names are user-defined. "
        "List name must be a non-empty string starting with an "
        "alphanumeric character or underscore. "
        "(it must match the regex: /^\\w+/)"
    )
    user_id: int | None = Field(
        default=None,
        description="ID of user that you want to add the listing to. "
        "If not given, will default to the associated user object that is posting.",
    )
    params: dict[str, Any] | None = Field(
        default=None,
        description='Optional parameters for "watchlist" type listings, when '
        "searching for new candidates around a given object. "
        "For example, if you want to search for new candidates around a given "
        "object, you can specify the search radius and the number of candidates "
        "to return. "
        "The parameters are passed to the microservice that is responsible for "
        "processing the listing. "
        "The microservice will return a list of candidates that match the given "
        "parameters, and ingest them.",
    )


class ListingPostResponse(BaseModel):
    """Data payload returned when adding a listing."""

    id: int = Field(description="New listing ID")


class ListingPatchBody(BaseModel):
    """Request body for updating a listing."""

    model_config = ConfigDict(extra="forbid")

    user_id: int | None = Field(
        default=None, description="ID of the user the listing belongs to."
    )
    obj_id: str | None = Field(default=None, description="ID of the listed object.")
    list_name: str | None = Field(
        default=None,
        description='Listing name for this item, e.g., "favorites". '
        "Multiple objects can be saved by the same user to different "
        "lists, where the list names are user-defined. "
        "List name must be a non-empty string starting with an "
        "alphanumeric character or underscore. "
        "(it must match the regex: /^\\w+/)",
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
    return re.search(r"^\w+", name) is not None


class UserObjListHandler(BaseHandler):
    @auth_or_token
    async def get(self, user_id: int | None = None):
        """
        ---
        summary: Get user object listings
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
        else:
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                return self.error(f"Invalid user_id: {user_id}")

        list_name = self.get_query_argument("listName", None)

        async with self.AsyncSession() as session:
            stmt = Listing.select(self.current_user).where(Listing.user_id == user_id)

            if list_name is not None:
                stmt = stmt.where(Listing.list_name == list_name)

            result = await session.scalars(stmt)
            return self.success(data=result.all())

    @auth_or_token
    async def post(self, *, body: ListingPostBody = None) -> ListingPostResponse:
        """
        ---
        summary: Add a listing
        description: Add a listing.
        tags:
        - listings
        """
        body = self.parse_body(ListingPostBody)

        user_id = body.user_id
        if user_id is None:
            user_id = self.associated_user_object.id

        if (
            user_id != self.associated_user_object.id
            and not self.associated_user_object.is_admin
        ):
            return self.error("Only admins can add listings to other users' accounts")

        obj_id = body.obj_id
        obj_check = Obj.get(obj_id, self.current_user)
        if obj_check is None:
            return self.error(f"Cannot find Obj with ID: {obj_id}")

        list_name = body.list_name
        if not check_list_name(list_name):
            return self.error(
                "Input `list_name` must begin with alphanumeric/underscore"
            )

        if list_name == "watchlist" and body.params is None:
            return self.error("Input `params` must be provided for `watchlist`")

        params = body.params

        if params is not None:
            if list_name == "watchlist":
                # verify that the params are "arcsec", "cadence", and "end_of_night"
                if "arcsec" not in params or "cadence" not in params:
                    return self.error(
                        "Input `params` must contain `arcsec` and `cadence`"
                    )
                if not isinstance(params["arcsec"], int | float) or not isinstance(
                    params["cadence"], int | float
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

        async with self.AsyncSession() as session:
            stmt = Listing.select(self.current_user).where(
                Listing.user_id == user_id,
                Listing.list_name == list_name,
                Listing.obj_id == obj_id,
            )

            # what to do if listing already exists...
            existing = await session.scalar(stmt)
            if existing is not None:
                return self.error(
                    f"Listing already exists with user_id={user_id}, "
                    f"obj_id={obj_id} and list_name={list_name}"
                )

            listing = Listing(
                user_id=user_id, obj_id=obj_id, list_name=list_name, params=params
            )

            session.add(listing)

            try:
                await session.commit()
            except AccessError as e:
                return self.error(str(e))

            if list_name == "favorites":
                self.push(action="skyportal/REFRESH_FAVORITES")
                self.push(action="skyportal/REFRESH_FAVORITE_SOURCES")
            if list_name == "rejected_candidates":
                self.push(action="skyportal/REFRESH_REJECTED_CANDIDATES")

            return self.success(data={"id": listing.id})

    @auth_or_token
    async def patch(self, listing_id: int, *, body: ListingPatchBody = None):
        """
        ---
        summary: Update a listing
        description: Update an existing listing
        tags:
        - listings
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
        body = self.parse_body(ListingPatchBody)
        async with self.AsyncSession() as session:
            listing = await session.scalar(
                Listing.select(self.current_user, mode="update").where(
                    Listing.id == listing_id
                )
            )
            if listing is None:
                return self.error(f"Cannot find listing with ID: {listing_id}")

            user_id = body.user_id if body.user_id is not None else listing.user_id
            if (
                user_id != self.associated_user_object.id
                and not self.current_user.is_system_admin
            ):
                return self.error("Insufficient permissions.")

            obj_id = body.obj_id if body.obj_id is not None else listing.obj_id
            obj_check = await session.scalar(
                Obj.select(self.current_user).where(Obj.id == obj_id)
            )
            if obj_check is None:
                return self.error(f"Cannot find Obj with ID: {obj_id}")

            list_name = (
                body.list_name if body.list_name is not None else listing.list_name
            )

            if not check_list_name(list_name):
                return self.error(
                    "Input `list_name` must begin with alphanumeric/underscore"
                )

            listing.user_id = user_id
            listing.obj_id = obj_id
            listing.list_name = list_name

            await session.commit()

            if list_name == "favorites":
                self.push(action="skyportal/REFRESH_FAVORITES")
                self.push(action="skyportal/REFRESH_FAVORITE_SOURCES")
            if list_name == "rejected_candidates":
                self.push(action="skyportal/REFRESH_REJECTED_CANDIDATES")

            return self.success()

    @auth_or_token
    async def delete(self, listing_id: int | None = None):
        """
        ---
        summary: Remove a listing
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
        async with self.AsyncSession() as session:
            if listing_id is not None:
                try:
                    listing_id = int(listing_id)
                except ValueError:
                    return self.error(f"Invalid listing_id {listing_id}")

                listing = await session.scalar(
                    Listing.select(self.current_user).where(Listing.id == listing_id)
                )
                if listing is None:
                    return self.error(f"Cannot find listing with ID: {listing_id}")
            else:
                data = self.get_json()

                schema = Listing.__schema__(exclude=["user_id"])
                user_id = data.pop("user_id", self.associated_user_object.id)

                try:
                    schema.load(data)
                except ValidationError as e:
                    return self.error(
                        f"Invalid/missing parameters: {e.normalized_messages()}"
                    )

                obj_id = data.get("obj_id")
                obj_test = await session.scalar(
                    Obj.select(self.current_user).where(Obj.id == obj_id)
                )
                if obj_test is None:
                    return self.error(f"Cannot find Obj with ID: {obj_id}")

                list_name = data.get("list_name")
                listing = await session.scalar(
                    Listing.select(self.current_user, mode="delete").where(
                        Listing.user_id == user_id,
                        Listing.obj_id == obj_id,
                        Listing.list_name == list_name,
                    )
                )

            if listing is None:
                return self.error("Cannot delete Listing.")

            list_name = listing.list_name

            await session.delete(listing)
            await session.commit()

            if list_name == "favorites":
                self.push(action="skyportal/REFRESH_FAVORITES")
                self.push(action="skyportal/REFRESH_FAVORITE_SOURCES")
            if list_name == "rejected_candidates":
                self.push(action="skyportal/REFRESH_REJECTED_CANDIDATES")

            return self.success()
