"""Typed endpoint functions for ``/api/brokers``."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models.brokers import (
    BrokerAlertSaveResponse,
    BrokerCapabilitiesResponse,
    BrokerClassname,
    BrokerFilterAttachResponse,
    BrokerFilterDetailResponse,
    BrokerFilterKind,
    BrokerFilterPostResponse,
    BrokerFilterQuery,
    BrokerFilterResponse,
    BrokerFiltersPageResponse,
    BrokerFilterValidationResponse,
    BrokerFilterVersionResponse,
    BrokerPost,
    BrokerPostResponse,
    BrokerResponse,
)

from skyportal_py._http import unwrap
from skyportal_py.photometry import PhotometryPointResponse

__all__ = [
    "BrokerAlertSaveResponse",
    "BrokerCapabilitiesResponse",
    "BrokerClassname",
    "BrokerFilterAttachResponse",
    "BrokerFilterDetailResponse",
    "BrokerFilterKind",
    "BrokerFilterPostResponse",
    "BrokerFilterQuery",
    "BrokerFilterResponse",
    "BrokerFilterValidationResponse",
    "BrokerFilterVersionResponse",
    "BrokerFiltersPageResponse",
    "BrokerPost",
    "BrokerPostResponse",
    "BrokerResponse",
]


def fetch_brokers(client: httpx.Client) -> list[BrokerResponse]:
    """Retrieve every broker visible to the token.

    ``altdata`` is only populated for system admins, and always has the
    provider's secret configuration fields stripped.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/brokers")
    return [BrokerResponse.model_validate(item) for item in unwrap(response)]


def fetch_broker(client: httpx.Client, broker_id: int) -> BrokerResponse:
    """Retrieve a single broker by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker.
    """
    response = client.get(f"/api/brokers/{broker_id}")
    return BrokerResponse.model_validate(unwrap(response))


def post_broker(client: httpx.Client, payload: BrokerPost) -> BrokerPostResponse:
    """Register a configured connection to an external alert broker.

    Requires the System admin ACL. A broker whose provider implements
    ``test_connection`` is always created inactive, since activating it is
    what checks its credentials.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : BrokerPost
        The broker to register. ``broker_classname`` must be a registered
        provider class name.
    """
    response = client.post("/api/brokers", json=payload.model_dump(exclude_none=True))
    return BrokerPostResponse.model_validate(unwrap(response))


def update_broker(  # noqa: PLR0913 -- mirrors the endpoint's body parameters
    client: httpx.Client,
    broker_id: int,
    *,
    name: str | None = None,
    active: bool | None = None,
    altdata: dict[str, Any] | None = None,
    default_alert_search: bool | None = None,
    default_crossmatch: bool | None = None,
) -> None:
    """Update a broker.

    Requires the System admin ACL. ``altdata`` is merged into the stored
    configuration, so blank or omitted values keep the stored credentials.
    Activating a broker whose provider implements ``test_connection``, or
    editing an active one's credentials, reaches the broker first and fails
    if the credentials are refused.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker to update.
    name : str, optional
        New broker name.
    active : bool, optional
        Whether the broker is active.
    altdata : dict, optional
        Endpoints and credentials to overlay on the stored configuration.
    default_alert_search : bool, optional
        Make this the broker the source page searches alerts on; the server
        clears the flag on every other broker.
    default_crossmatch : bool, optional
        Make this the broker cross-matches are run against; the server
        clears the flag on every other broker.
    """
    fields = {
        "name": name,
        "active": active,
        "altdata": altdata,
        "default_alert_search": default_alert_search,
        "default_crossmatch": default_crossmatch,
    }
    payload = {key: value for key, value in fields.items() if value is not None}
    unwrap(client.patch(f"/api/brokers/{broker_id}", json=payload))


def delete_broker(client: httpx.Client, broker_id: int) -> None:
    """Delete a broker.

    Requires the System admin ACL.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker to delete.
    """
    unwrap(client.delete(f"/api/brokers/{broker_id}"))


def fetch_broker_alerts(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    broker_id: int,
    *,
    object_id: str | None = None,
    candid: int | str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    radius: float | None = None,
    jd_start: float | None = None,
    jd_end: float | None = None,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Search a broker's alerts.

    The query is dispatched to the broker's provider, so the accepted
    parameters and the shape of each alert are provider-specific. The server
    injects the requester's stream-derived access scope. The broker must be
    active and implement ``query_alerts``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker to query.
    object_id : str, optional
        Restrict to alerts of this object.
    candid : int or str, optional
        Restrict to this alert candidate ID.
    ra, dec, radius : float, optional
        Cone-search filter; provide all three together.
    jd_start, jd_end : float, optional
        Bound the alert JD; either bound alone is valid. Honouring these is
        best effort, so a provider may ignore them.
    extra_params : dict, optional
        Additional provider-specific query parameters.
    """
    params: dict[str, Any] = dict(extra_params or {})
    if object_id is not None:
        params["objectId"] = object_id
    if candid is not None:
        params["candid"] = candid
    if ra is not None:
        params["ra"] = ra
    if dec is not None:
        params["dec"] = dec
    if radius is not None:
        params["radius"] = radius
    if jd_start is not None:
        params["jd_start"] = jd_start
    if jd_end is not None:
        params["jd_end"] = jd_end
    response = client.get(f"/api/brokers/{broker_id}/alerts", params=params)
    return list(unwrap(response))


def fetch_broker_alert(
    client: httpx.Client,
    broker_id: int,
    alert_id: str,
    *,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Retrieve a single alert from a broker.

    Dispatched to the broker's provider, which returns the alert with its
    auxiliary/history data if available. The broker must be active and
    implement ``get_alert``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker to query.
    alert_id : str
        Alert identifier the provider keys alerts on.
    extra_params : dict, optional
        Additional provider-specific query parameters.
    """
    response = client.get(
        f"/api/brokers/{broker_id}/alerts/{alert_id}",
        params=dict(extra_params or {}),
    )
    return unwrap(response)


def fetch_broker_cutouts(
    client: httpx.Client,
    broker_id: int,
    alert_id: str,
    *,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Retrieve an alert's science, template and difference cutouts.

    Dispatched to the broker's provider, which returns a JSON payload rather
    than raw image bytes. The broker must be active and implement
    ``get_cutouts``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker to query.
    alert_id : str
        Alert identifier (e.g. candid) the provider keys cutouts on.
    extra_params : dict, optional
        Additional provider-specific query parameters.
    """
    response = client.get(
        f"/api/brokers/{broker_id}/alerts/{alert_id}/cutouts",
        params=dict(extra_params or {}),
    )
    return unwrap(response)


def fetch_broker_photometry(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    broker_id: int,
    alert_id: str,
    *,
    survey: str | None = None,
    fmt: str = "mag",
    magsys: str = "ab",
    refresh: bool = False,
) -> list[PhotometryPointResponse]:
    """Retrieve an object's photometry merged with the broker's.

    The persisted, access-controlled database photometry is merged with
    photometry fetched on demand from the broker, deduped by instrument,
    filter and MJD. The broker half is cached per access scope and never
    written to the database. The broker must be active and implement
    ``get_photometry``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker to query.
    alert_id : str
        Object identifier to fetch photometry for.
    survey : str, optional
        Survey to fetch the broker photometry from.
    fmt : str, optional
        Photometry format, ``"mag"`` by default.
    magsys : str, optional
        Magnitude system, ``"ab"`` by default.
    refresh : bool, optional
        Bypass any cached broker payload and re-fetch.
    """
    params: dict[str, Any] = {
        "format": fmt,
        "magsys": magsys,
        "refresh": refresh,
    }
    if survey is not None:
        params["survey"] = survey
    response = client.get(
        f"/api/brokers/{broker_id}/alerts/{alert_id}/photometry",
        params=params,
    )
    return [PhotometryPointResponse.model_validate(item) for item in unwrap(response)]


def fetch_broker_survey_photometry(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    object_id: str,
    *,
    survey: str,
    fmt: str = "mag",
    magsys: str = "ab",
    refresh: bool = False,
) -> list[PhotometryPointResponse]:
    """Retrieve an object's photometry via the survey's own broker.

    BrokerResponse-address-free variant of :func:`fetch_broker_photometry`: the
    server resolves the first active broker serving ``survey`` that
    implements ``get_photometry``. If no such broker is configured, it
    degrades to the object's database photometry.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    object_id : str
        Object identifier to fetch photometry for.
    survey : str
        Survey whose broker should serve the photometry; required.
    fmt : str, optional
        Photometry format, ``"mag"`` by default.
    magsys : str, optional
        Magnitude system, ``"ab"`` by default.
    refresh : bool, optional
        Bypass any cached broker payload and re-fetch.
    """
    params: dict[str, Any] = {
        "survey": survey,
        "format": fmt,
        "magsys": magsys,
        "refresh": refresh,
    }
    response = client.get(f"/api/brokers/photometry/{object_id}", params=params)
    return [PhotometryPointResponse.model_validate(item) for item in unwrap(response)]


def post_broker_alert_save(
    client: httpx.Client,
    broker_id: int,
    alert_id: str,
    group_ids: list[int],
) -> BrokerAlertSaveResponse:
    """Save a broker alert as a skyportal source.

    Requires the Upload data ACL. The object and its photometry (and
    cutouts, when the provider can serve them) are ingested through the
    broker's provider. The broker must be active and implement
    ``save_as_source``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker holding the alert.
    alert_id : str
        Object identifier to save.
    group_ids : list of int
        Groups to save the source to; at least one is required.
    """
    response = client.post(
        f"/api/brokers/{broker_id}/alerts/{alert_id}/save",
        json={"group_ids": group_ids},
    )
    return BrokerAlertSaveResponse.model_validate(unwrap(response))


def fetch_broker_cone_search(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    broker_id: int,
    *,
    ra: float,
    dec: float,
    radius: float,
    radius_units: str = "arcsec",
) -> dict[str, Any]:
    """Cross-match a position against a broker's archival catalogs.

    Returns the matched sources keyed by catalog name (e.g. Gaia, PS1,
    AllWISE). The broker must be active and implement ``cone_search``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker to cross-match against.
    ra : float
        Right ascension in degrees, ``0 <= ra < 360``; required.
    dec : float
        Declination in degrees, ``-90 <= dec <= 90``; required.
    radius : float
        Search radius, in ``radius_units``; required.
    radius_units : str, optional
        One of ``"deg"``, ``"arcmin"`` or ``"arcsec"`` (the default).
    """
    params: dict[str, Any] = {
        "ra": ra,
        "dec": dec,
        "radius": radius,
        "radius_units": radius_units,
    }
    response = client.get(f"/api/brokers/{broker_id}/cone_search", params=params)
    return unwrap(response)


def fetch_broker_filters(
    client: httpx.Client, broker_id: int
) -> list[BrokerFilterResponse]:
    """Retrieve the skyportal filters attached to a broker.

    The broker must be active.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker.
    """
    response = client.get(f"/api/brokers/{broker_id}/filters")
    return [BrokerFilterResponse.model_validate(item) for item in unwrap(response)]


def fetch_broker_filter(
    client: httpx.Client,
    broker_id: int,
    filter_id: int,
) -> BrokerFilterDetailResponse:
    """Retrieve one broker filter with its broker-side versions and state.

    The version fields (``fv``, ``active_fid``, ``active``, ``filters``) are
    only populated for broker-managed filters, and are omitted when the
    broker is unreachable.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker the filter is attached to.
    filter_id : int
        ID of the skyportal filter.
    """
    response = client.get(f"/api/brokers/{broker_id}/filters/{filter_id}")
    return BrokerFilterDetailResponse.model_validate(unwrap(response))


def post_broker_filter(  # noqa: PLR0913 -- mirrors the endpoint's body parameters
    client: httpx.Client,
    broker_id: int,
    filter_id: int,
    *,
    altdata: dict[str, Any] | list[Any] | None = None,
    filters: dict[str, Any] | list[Any] | None = None,
    query: BrokerFilterQuery | None = None,
    autosave: bool | None = None,
) -> BrokerFilterPostResponse:
    """Create a broker-side filter version on an existing skyportal filter.

    Requires the Upload data ACL. What the body must carry depends on the
    broker's ``filter_kind``: a ``"query"`` broker (e.g. Lasair) takes
    ``query`` and stores it on the skyportal filter, while a ``"pipeline"``
    broker (e.g. BOOM) takes ``altdata`` (the compiled native filter) and
    ``filters`` (the editable version tree), and the broker-side ids are
    stored in the filter's altdata. The broker must be active.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker to create the filter version on.
    filter_id : int
        ID of the existing skyportal filter; required.
    altdata : dict or list, optional
        Compiled native filter forwarded to a pipeline broker.
    filters : dict or list, optional
        Editable version tree stored alongside the broker-side version id.
    query : BrokerFilterQuery, optional
        Saved query for a ``"query"``-kind broker.
    autosave : bool, optional
        Whether the skyportal filter auto-saves passing objects, for a
        ``"query"``-kind broker.
    """
    payload: dict[str, Any] = {}
    if altdata is not None:
        payload["altdata"] = altdata
    if filters is not None:
        payload["filters"] = filters
    if query is not None:
        payload["query"] = query.model_dump(exclude_none=True)
    if autosave is not None:
        payload["autosave"] = autosave
    response = client.post(
        f"/api/brokers/{broker_id}/filters/{filter_id}",
        json=payload,
    )
    return BrokerFilterPostResponse.model_validate(unwrap(response))


def update_broker_filter(  # noqa: PLR0913 -- mirrors the endpoint's body parameters
    client: httpx.Client,
    broker_id: int,
    filter_id: int,
    *,
    active: bool | None = None,
    active_fid: str | int | None = None,
    auto_annotate: bool | None = None,
    auto_save: bool | None = None,
    auto_followup: bool | None = None,
) -> None:
    """Update a broker filter's activation or automation flags.

    Requires the Upload data ACL. ``active`` and ``active_fid`` must be
    given together to change which version is active, and a version can only
    be activated once it has a passing validation on record (see
    :func:`post_broker_filter_validation`) unless the token belongs to a
    system admin. The broker must be active.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker the filter is attached to.
    filter_id : int
        ID of the broker-managed skyportal filter.
    active : bool, optional
        Whether the selected version runs on the broker.
    active_fid : str or int, optional
        BrokerResponse-side id of the version to activate.
    auto_annotate : bool, optional
        Annotate objects passing the filter.
    auto_save : bool, optional
        Save objects passing the filter as sources.
    auto_followup : bool, optional
        Trigger follow-up for objects passing the filter.
    """
    fields = {
        "active": active,
        "active_fid": active_fid,
        "autoAnnotate": auto_annotate,
        "autoSave": auto_save,
        "autoFollowup": auto_followup,
    }
    payload = {key: value for key, value in fields.items() if value is not None}
    unwrap(client.patch(f"/api/brokers/{broker_id}/filters/{filter_id}", json=payload))


def delete_broker_filter(
    client: httpx.Client,
    broker_id: int,
    filter_id: int,
) -> None:
    """Delete a broker filter.

    Requires the Upload data ACL. The skyportal filter is deleted, and its
    broker-side filter is deleted best-effort through the provider. The
    broker must be active.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker the filter is attached to.
    filter_id : int
        ID of the skyportal filter to delete.
    """
    unwrap(client.delete(f"/api/brokers/{broker_id}/filters/{filter_id}"))


def fetch_broker_filter_catalog(  # noqa: PLR0913 -- mirrors the endpoint's query parameters
    client: httpx.Client,
    *,
    page_number: int = 1,
    num_per_page: int = 25,
    name: str | None = None,
    group_id: int | None = None,
    stream_id: int | None = None,
    broker_id: int | str | None = None,
) -> BrokerFiltersPageResponse:
    """Query the filters visible to the token and the broker they belong to.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    page_number, num_per_page : int, optional
        Pagination controls; the server caps ``num_per_page`` at 100.
    name : str, optional
        Case-insensitive substring of the filter name.
    group_id : int, optional
        Restrict to filters of this group.
    stream_id : int, optional
        Restrict to filters of this stream.
    broker_id : int or str, optional
        Restrict to filters attached to this broker, or pass ``"none"`` for
        the filters attached to no broker.
    """
    params: dict[str, Any] = {
        "pageNumber": page_number,
        "numPerPage": num_per_page,
    }
    if name is not None:
        params["name"] = name
    if group_id is not None:
        params["groupID"] = group_id
    if stream_id is not None:
        params["streamID"] = stream_id
    if broker_id is not None:
        params["brokerID"] = broker_id
    response = client.get("/api/brokers/filters", params=params)
    return BrokerFiltersPageResponse.model_validate(unwrap(response))


def post_broker_filter_attach(
    client: httpx.Client,
    filter_id: int,
    broker_id: int,
) -> BrokerFilterAttachResponse:
    """Attach an unattached skyportal filter to a broker.

    Requires the Upload data ACL. The broker must be active and must accept
    filters, and the filter must not already belong to another broker.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    filter_id : int
        ID of the skyportal filter to attach.
    broker_id : int
        ID of the broker to attach it to.
    """
    response = client.post(
        f"/api/brokers/filters/{filter_id}/attach",
        json={"broker_id": broker_id},
    )
    return BrokerFilterAttachResponse.model_validate(unwrap(response))


def post_broker_filter_test(
    client: httpx.Client,
    broker_id: int,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    """Preview a filter against a broker without saving it.

    The body is filter parameters specific to the broker's ``filter_kind``
    (e.g. Lasair's ``selected``/``tables``/``conditions``, BOOM's pipeline),
    and the result is a count or a page of matching alerts. The server
    injects the requester's stream-derived access scope. The broker must be
    active and implement ``test_filter``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker to run the filter on.
    params : dict, optional
        Provider-specific filter parameters.
    """
    response = client.post(
        f"/api/brokers/{broker_id}/filter/test",
        json=params or {},
    )
    return unwrap(response)


def post_broker_filter_validation(
    client: httpx.Client,
    broker_id: int,
    filter_id: int,
    *,
    fid: str | int | None = None,
) -> BrokerFilterValidationResponse:
    """Validate a broker filter version for activation.

    The broker runs its activation validation without changing state, and
    skyportal records the verdict on the filter: activating a version
    through :func:`update_broker_filter` is gated on it. The broker must be
    active and implement ``validate_filter``, and the filter must be
    broker-managed.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker the filter is attached to.
    filter_id : int
        ID of the broker-managed skyportal filter.
    fid : str or int, optional
        BrokerResponse-side id of the version to validate; defaults to the broker's
        own choice of version.
    """
    payload: dict[str, Any] = {}
    if fid is not None:
        payload["fid"] = fid
    response = client.post(
        f"/api/brokers/{broker_id}/filters/{filter_id}/validate",
        json=payload,
    )
    return BrokerFilterValidationResponse.model_validate(unwrap(response))


def fetch_broker_filter_modules(
    client: httpx.Client,
    broker_id: int,
    *,
    survey: str | None = None,
    elements: str = "schema",
) -> dict[str, Any] | list[Any]:
    """Retrieve a broker's filter-building vocabulary.

    Returns the fields, operators and broker-scoped custom variables the
    broker's filters support, which drives the filter builder. The broker
    must be active and implement ``filter_modules``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker.
    survey : str, optional
        Survey to return the vocabulary for.
    elements : str, optional
        ``"schema"`` (the default) for the full schema, or one of
        ``"variables"``, ``"listVariables"``, ``"switchCases"`` or
        ``"blocks"`` for the stored custom elements of that kind.
    """
    params: dict[str, Any] = {"elements": elements}
    if survey is not None:
        params["survey"] = survey
    response = client.get(f"/api/brokers/{broker_id}/filter_modules", params=params)
    return unwrap(response)


def fetch_broker_filter_module(
    client: httpx.Client,
    broker_id: int,
    name: str,
    *,
    survey: str | None = None,
    elements: str = "schema",
) -> dict[str, Any] | None:
    """Retrieve one named module from a broker's filter-building vocabulary.

    The server returns ``None`` when the broker has no module of that name.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker.
    name : str
        Name of the module.
    survey : str, optional
        Survey to return the module for.
    elements : str, optional
        ``"schema"`` (the default) or one of ``"variables"``,
        ``"listVariables"``, ``"switchCases"`` or ``"blocks"``.
    """
    params: dict[str, Any] = {"elements": elements}
    if survey is not None:
        params["survey"] = survey
    response = client.get(
        f"/api/brokers/{broker_id}/filter_modules/{name}",
        params=params,
    )
    return unwrap(response)


def post_broker_filter_module(
    client: httpx.Client,
    broker_id: int,
    name: str,
    elements: str,
    data: dict[str, Any],
) -> None:
    """Create a broker-scoped custom filter module.

    Requires the Upload data ACL. Where the module is stored is up to the
    broker's provider. The broker must be active and implement
    ``filter_modules``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker to store the module on.
    name : str
        Name of the module.
    elements : str
        Kind of element: ``"variables"``, ``"listVariables"``,
        ``"switchCases"`` or ``"blocks"``.
    data : dict
        The module definition.
    """
    unwrap(
        client.post(
            f"/api/brokers/{broker_id}/filter_modules/{name}",
            json={"elements": elements, "data": data},
        )
    )


def update_broker_filter_module(
    client: httpx.Client,
    broker_id: int,
    name: str,
    elements: str,
    data: dict[str, Any],
) -> None:
    """Update a broker-scoped custom filter module.

    Requires the Upload data ACL. The server errors if no module of that
    name exists. The broker must be active and implement
    ``filter_modules``.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    broker_id : int
        ID of the broker holding the module.
    name : str
        Name of the module to update.
    elements : str
        Kind of element: ``"variables"``, ``"listVariables"``,
        ``"switchCases"`` or ``"blocks"``.
    data : dict
        The new module definition, merged into the stored one.
    """
    unwrap(
        client.put(
            f"/api/brokers/{broker_id}/filter_modules/{name}",
            json={"elements": elements, "data": data},
        )
    )
