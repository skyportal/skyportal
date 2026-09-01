"""Response models for ``/api/newsfeed``."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NewsFeedAuthorInfoResponse(BaseModel):
    """Display information about the user behind a news feed item.

    Exactly the fields ``basic_user_display_info`` (and
    ``Comment.construct_author_info_dict``) copies off the ``User``.
    """

    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    gravatar_url: str | None = None
    is_bot: bool | None = None


class NewsFeedItemResponse(BaseModel):
    """One entry in the news feed (no database model; built by the handler).

    ``author`` is only set on comment items; ``author_info`` is absent on
    source items.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "source",
        "comment",
        "classification",
        "spectrum",
        "photometry",
    ]
    time: datetime | None = None
    message: str | None = None
    source_id: str | None = None
    classification: str | None = None
    author: str | None = None
    author_info: NewsFeedAuthorInfoResponse | None = None


MAX_NEWSFEED_ITEMS = 1000


DEFAULT_NEWSFEED_ITEMS = 50


class NewsFeedGetQuery(BaseModel):
    """Query parameters for the news feed."""

    model_config = ConfigDict(extra="forbid")

    numItems: int | None = Field(
        default=None,
        description=(
            "Number of newsfeed items to return. "
            f"Defaults to {DEFAULT_NEWSFEED_ITEMS}. Max is {MAX_NEWSFEED_ITEMS}."
        ),
    )
    teamID: int | None = Field(
        default=None,
        description="Scope the feed to the groups of this team, intersected with "
        "the user's accessible groups.",
    )
