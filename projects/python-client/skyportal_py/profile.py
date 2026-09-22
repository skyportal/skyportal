"""Typed endpoint functions for ``/api/internal/profile``."""

from __future__ import annotations

import httpx
from skyportal_py_models.profile import (
    ProfilePatch,
    ProfileTokenResponse,
    UserProfileResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "ProfilePatch",
    "ProfileTokenResponse",
    "UserProfileResponse",
]


def fetch_profile(client: httpx.Client) -> UserProfileResponse:
    """Retrieve the profile of the user associated with the token."""
    return UserProfileResponse.model_validate(
        unwrap(client.get("/api/internal/profile"))
    )


def update_profile(
    client: httpx.Client,
    payload: ProfilePatch,
    *,
    user_id: int | None = None,
) -> None:
    """Update a user's profile and preferences.

    Only the provided fields are sent; omitted fields are left unchanged.
    ``preferences`` is merged into the stored preferences dict rather than
    replacing it.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : ProfilePatch
        The fields to change.
    user_id : int, optional
        UserResponse whose profile to update; defaults to the token's own user.
        Updating another user requires the "Manage users" ACL.
    """
    path = (
        "/api/internal/profile"
        if user_id is None
        else f"/api/internal/profile/{user_id}"
    )
    unwrap(client.patch(path, json=payload.model_dump(exclude_none=True)))
