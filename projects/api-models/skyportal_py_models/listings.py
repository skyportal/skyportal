"""Response models for ``/api/listing``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ListingResponse(BaseModel):
    """An object saved by a user to a named list (``Listing``)."""

    # The handler returns bare ``Listing`` rows, so the ``user`` and ``obj``
    # relationships are never loaded and are not declared here.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    user_id: int | None = None
    obj_id: str | None = None
    list_name: str | None = None
    params: dict[str, Any] | None = None


class ListingPost(BaseModel):
    """Payload for adding an object to a user's list."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    list_name: str
    user_id: int | None = None
    params: dict[str, Any] | None = None


class UserObjListGetQuery(BaseModel):
    """Query parameters for retrieving sources from a user's lists."""

    model_config = ConfigDict(extra="forbid")

    listName: str | None = Field(
        default=None,
        description="Name of the list to retrieve objects from. "
        "If not given will return all objects saved by the user to all lists.",
    )


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


class ListingDeleteBody(BaseModel):
    """Request body for removing a listing by obj_id and list_name (used when no
    listing_id path parameter is supplied)."""

    model_config = ConfigDict(extra="forbid")

    user_id: int | None = Field(
        default=None,
        description="ID of user that you want to add the listing to. "
        "If not given, will default to the associated user object that is posting.",
    )
    obj_id: str | None = Field(default=None, description="ID of the listed object.")
    list_name: str | None = Field(
        default=None,
        description='Listing name for this item, e.g., "favorites".',
    )
