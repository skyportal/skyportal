"""Typed endpoint functions for ``/api/newsfeed``."""

from __future__ import annotations

import httpx
from skyportal_py_models.news_feed import (
    NewsFeedAuthorInfoResponse,
    NewsFeedItemResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "NewsFeedAuthorInfoResponse",
    "NewsFeedItemResponse",
]


def fetch_news_feed(
    client: httpx.Client,
    *,
    num_items: int | None = None,
    team_id: int | None = None,
) -> list[NewsFeedItemResponse]:
    """Retrieve a summary of recent activity, newest first.

    Items cover new sources, comments, classifications, spectra and follow-up
    photometry; which categories appear, and whether bot comments and ML
    classifications are included, follow the user's news feed preferences.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    num_items : int, optional
        Number of items to return. The server takes the larger of this and the
        user's preference, defaults to ``50`` when neither is set, and rejects
        values above ``1000``.
    team_id : int, optional
        Restrict the feed to sources saved to this team's groups; a view
        filter only, always intersected with the token's accessible groups.
    """
    params: dict[str, int] = {}
    if num_items is not None:
        params["numItems"] = num_items
    if team_id is not None:
        params["teamID"] = team_id
    response = client.get("/api/newsfeed", params=params)
    return [NewsFeedItemResponse.model_validate(item) for item in unwrap(response)]
