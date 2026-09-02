"""Typed endpoint functions for ``/api/objs`` and related endpoints."""

from __future__ import annotations

import httpx
from skyportal_py_models.objs import (
    ObjPositionResponse,
    SuperObjMemberResponse,
    SuperObjPostResponse,
    SuperObjResponse,
)

from skyportal_py._http import unwrap, unwrap_content

__all__ = [
    "ObjPositionResponse",
    "SuperObjMemberResponse",
    "SuperObjPostResponse",
    "SuperObjResponse",
]


def delete_obj(client: httpx.Client, obj_id: str) -> None:
    """Delete an object.

    The server refuses to delete objects that still have associated
    annotations, spectra, photometry, photometric series, comments,
    classifications, or GCN-event links; remove those first.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID to delete, e.g. ``"ZTF20abcdef"``.
    """
    unwrap(client.delete(f"/api/objs/{obj_id}"))


def fetch_obj_position(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    obj_id: str,
    *,
    instrument_ids: list[int] | None = None,
    stream_ids: list[int] | None = None,
    stream_only: bool = False,
    snr_threshold: float = 3.0,
    method: str = "snr2",
) -> ObjPositionResponse:
    """Calculate an object's position from its photometry.

    Forced photometry is always excluded. If no photometry passes the
    filters, the server falls back to the discovery position.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source, e.g. ``"ZTF20abcdef"``.
    instrument_ids : list of int, optional
        Only use photometry from these instruments.
    stream_ids : list of int, optional
        Only use photometry from these streams.
    stream_only : bool, optional
        Only use photometry associated with at least one stream. Ignored
        if ``stream_ids`` is provided.
    snr_threshold : float, optional
        Only use photometry with a signal-to-noise ratio above this
        positive value. Defaults to 3.0.
    method : str, optional
        Position-weighting method, one of ``"snr2"`` or ``"invvar"``.
    """
    params: dict[str, str | float] = {
        "snr_threshold": snr_threshold,
        "method": method,
    }
    if instrument_ids is not None:
        params["instrument_ids"] = ",".join(str(i) for i in instrument_ids)
    if stream_ids is not None:
        params["stream_ids"] = ",".join(str(i) for i in stream_ids)
    if stream_only:
        params["stream_only"] = "true"
    response = client.get(f"/api/sources/{obj_id}/position", params=params)
    return ObjPositionResponse.model_validate(unwrap(response))


def post_super_obj(
    client: httpx.Client,
    *,
    name: str | None = None,
    is_roid: bool = False,
    obj_ids: list[str] | None = None,
) -> SuperObjPostResponse:
    """Create a super-object linking multiple objects.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    name : str, optional
        Name of the super-object, e.g. an MPC designation.
    is_roid : bool, optional
        Whether the super-object is a moving object.
    obj_ids : list of str, optional
        IDs of the objects to link.
    """
    payload: dict[str, str | bool | list[str]] = {"is_roid": is_roid}
    if name is not None:
        payload["name"] = name
    if obj_ids is not None:
        payload["obj_ids"] = obj_ids
    response = client.post("/api/super_objs", json=payload)
    return SuperObjPostResponse.model_validate(unwrap(response))


def fetch_super_obj(client: httpx.Client, super_obj_id: int) -> SuperObjResponse:
    """Retrieve a single super-object by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    super_obj_id : int
        ID of the super-object.
    """
    response = client.get(f"/api/super_objs/{super_obj_id}")
    return SuperObjResponse.model_validate(unwrap(response))


def fetch_super_objs(
    client: httpx.Client,
    *,
    name: str | None = None,
    is_roid: bool | None = None,
    obj_id: str | None = None,
) -> list[SuperObjResponse]:
    """Query super-objects.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    name : str, optional
        Restrict to super-objects whose name contains this string.
    is_roid : bool, optional
        Restrict by moving-object status.
    obj_id : str, optional
        Restrict to super-objects linking this object.
    """
    params: dict[str, str | bool] = {}
    if name is not None:
        params["name"] = name
    if is_roid is not None:
        params["isRoid"] = is_roid
    if obj_id is not None:
        params["objID"] = obj_id
    response = client.get("/api/super_objs", params=params)
    return [SuperObjResponse.model_validate(item) for item in unwrap(response)]


def update_super_obj(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    super_obj_id: int,
    *,
    name: str | None = None,
    is_roid: bool | None = None,
    obj_ids: list[str] | None = None,
    add_obj_ids: list[str] | None = None,
    remove_obj_ids: list[str] | None = None,
) -> None:
    """Update a super-object's metadata or membership.

    ``obj_ids`` replaces the membership wholesale; ``add_obj_ids`` and
    ``remove_obj_ids`` modify it incrementally and may not be combined
    with ``obj_ids``. Only the provided fields are sent.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    super_obj_id : int
        ID of the super-object to update.
    name : str, optional
        New name.
    is_roid : bool, optional
        New moving-object status.
    obj_ids : list of str, optional
        Replacement list of linked object IDs.
    add_obj_ids, remove_obj_ids : list of str, optional
        Object IDs to add to or remove from the membership.
    """
    fields = {
        "name": name,
        "is_roid": is_roid,
        "obj_ids": obj_ids,
        "add_obj_ids": add_obj_ids,
        "remove_obj_ids": remove_obj_ids,
    }
    payload = {key: value for key, value in fields.items() if value is not None}
    unwrap(client.patch(f"/api/super_objs/{super_obj_id}", json=payload))


def delete_super_obj(client: httpx.Client, super_obj_id: int) -> None:
    """Delete a super-object, leaving its linked objects untouched.

    Requires the "System admin" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    super_obj_id : int
        ID of the super-object to delete.
    """
    unwrap(client.delete(f"/api/super_objs/{super_obj_id}"))


def fetch_unsourced_finding_chart(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    location_type: str,
    catalog_id: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    imsize: float = 4.0,
    facility: str = "Keck",
    image_source: str = "ps1",
    use_ztfref: bool = True,
    obstime: str | None = None,
    output_type: str = "pdf",
    num_offset_stars: int = 3,
) -> bytes:
    """Generate a finding chart for an arbitrary position or Gaia ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    location_type : str
        One of ``"gaia_dr3"``, ``"gaia_dr2"``, or ``"pos"``. For ``"pos"``,
        provide ``ra`` and ``dec``; otherwise provide ``catalog_id`` and
        the position is pulled from the Gaia catalog.
    catalog_id : str, optional
        Gaia source ID (digits only); required unless ``location_type``
        is ``"pos"``.
    ra, dec : float, optional
        Position of interest in degrees, at the time of observation (the
        caller is responsible for proper-motion corrections).
    imsize : float, optional
        Square image size in arcmin, in [2, 15]. Defaults to 4.0.
    facility : str, optional
        Starlist format, one of ``"Keck"``, ``"Shane"``, ``"P200"``, or
        ``"P200-NGPS"``. Defaults to ``"Keck"``.
    image_source : str, optional
        Chart image source, one of ``"ps1"``, ``"desi"``, ``"dss"``, or
        ``"ztfref"``. Defaults to ``"ps1"``.
    use_ztfref : bool, optional
        Use the ZTFref catalog for offset-star positions instead of Gaia
        DR3. Defaults to True.
    obstime : str, optional
        ObservationResponse time in ISO format, e.g. ``"2020-12-30T12:34:10"``.
        Defaults to now.
    output_type : str, optional
        Output file type, ``"pdf"`` or ``"png"``. Defaults to ``"pdf"``.
    num_offset_stars : int, optional
        Number of offset stars to determine and show, in [0, 4].
        Defaults to 3.
    """
    params: dict[str, str | float | int | bool] = {
        "location_type": location_type,
        "imsize": imsize,
        "facility": facility,
        "image_source": image_source,
        "use_ztfref": use_ztfref,
        "type": output_type,
        "num_offset_stars": num_offset_stars,
    }
    if catalog_id is not None:
        params["catalog_id"] = catalog_id
    if ra is not None:
        params["ra"] = ra
    if dec is not None:
        params["dec"] = dec
    if obstime is not None:
        params["obstime"] = obstime
    response = client.get("/api/unsourced_finder", params=params)
    return unwrap_content(response)
