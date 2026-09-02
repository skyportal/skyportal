"""Typed endpoint functions for ``/api/sharing``."""

from __future__ import annotations

import httpx

from skyportal_py._http import unwrap


def post_sharing(
    client: httpx.Client,
    group_ids: list[int],
    *,
    photometry_ids: list[int] | None = None,
    spectrum_ids: list[int] | None = None,
) -> None:
    """Share photometry and/or spectra with additional groups or users.

    At least one of ``photometry_ids`` or ``spectrum_ids`` must be given.
    Sharing is additive: groups already attached to a point or spectrum are
    left in place. Sharing photometry you do not own requires membership in
    every target group plus sharing rights in one of the point's current
    groups, unless you are a system admin. Spectra can only be shared by
    users with update access to them.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_ids : list of int
        IDs of the groups the data will be shared with. To share with a
        single user, pass that user's single-user group ID.
    photometry_ids : list of int, optional
        IDs of the photometry points to share.
    spectrum_ids : list of int, optional
        IDs of the spectra to share.
    """
    payload: dict[str, list[int]] = {"groupIDs": group_ids}
    if photometry_ids is not None:
        payload["photometryIDs"] = photometry_ids
    if spectrum_ids is not None:
        payload["spectrumIDs"] = spectrum_ids
    unwrap(client.post("/api/sharing", json=payload))
