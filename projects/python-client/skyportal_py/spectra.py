"""Typed endpoint functions for spectra."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models.spectra import (
    BulkSpectraResponse,
    BulkSpectraSourceResponse,
    BulkSpectrumResponse,
    ParsedSpectrumResponse,
    SourceSpectraResponse,
    SpectrumAsciiParse,
    SpectrumAsciiPost,
    SpectrumDetailResponse,
    SpectrumPost,
    SpectrumPostResponse,
    SpectrumResponse,
    SpectrumUpdate,
    _SpectrumBaseResponse,
)

from skyportal_py._http import unwrap

__all__ = [
    "BulkSpectraResponse",
    "BulkSpectraSourceResponse",
    "BulkSpectrumResponse",
    "ParsedSpectrumResponse",
    "SourceSpectraResponse",
    "SpectrumAsciiParse",
    "SpectrumAsciiPost",
    "SpectrumDetailResponse",
    "SpectrumPost",
    "SpectrumPostResponse",
    "SpectrumResponse",
    "SpectrumUpdate",
    "_SpectrumBaseResponse",
]


def fetch_spectrum(
    client: httpx.Client,
    spectrum_id: int,
    *,
    include_original_file: bool = False,
) -> SpectrumResponse:
    """Retrieve a single spectrum by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    spectrum_id : int
        ID of the spectrum.
    include_original_file : bool, optional
        Also return the file the spectrum was originally uploaded from, in
        ``original_file_string``/``original_file_filename``.
    """
    response = client.get(
        f"/api/spectrum/{spectrum_id}",
        params={"includeOriginalFile": include_original_file},
    )
    return SpectrumResponse.model_validate(unwrap(response))


def fetch_spectra(  # noqa: PLR0913 -- mirrors the query parameters
    client: httpx.Client,
    obj_id: str,
    *,
    include_original_file: bool = False,
    normalization: str | None = None,
    sort_by: str = "observed_at",
    sort_order: str = "asc",
) -> list[SpectrumResponse]:
    """Retrieve the spectra of a source.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID of the source, e.g. ``"ZTF20abcdef"``.
    include_original_file : bool, optional
        Also return each spectrum's originally uploaded file, in
        ``original_file_string``/``original_file_filename``.
    normalization : str, optional
        Normalize each spectrum's fluxes before returning; the only
        supported scheme is ``"median"`` (median absolute flux becomes 1).
        Omitted returns the original fluxes.
    sort_by : str, optional
        Column to order the spectra by, ``"observed_at"`` or
        ``"created_at"``.
    sort_order : str, optional
        Sort direction, ``"asc"`` or ``"desc"``.
    """
    params: dict[str, str | bool] = {
        "includeOriginalFile": include_original_file,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }
    if normalization is not None:
        params["normalization"] = normalization
    response = client.get(f"/api/sources/{obj_id}/spectra", params=params)
    return SourceSpectraResponse.model_validate(unwrap(response)).spectra


def post_spectrum(client: httpx.Client, payload: SpectrumPost) -> SpectrumPostResponse:
    """Post a spectrum.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : SpectrumPost
        The spectrum to post. ``observed_at`` is an ISO-format (UTC)
        timestamp. If ``group_ids`` is omitted, the server applies its
        default visibility; the string ``"all"`` shares the spectrum with
        every group the token can access. Setting ``external_pi``,
        ``external_reducer`` or ``external_observer`` requires the matching
        ``pi``, ``reduced_by`` or ``observed_by`` list of user IDs.
    """
    response = client.post("/api/spectrum", json=payload.model_dump(exclude_none=True))
    return SpectrumPostResponse.model_validate(unwrap(response))


def delete_spectrum(client: httpx.Client, spectrum_id: int) -> None:
    """Delete a spectrum.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    spectrum_id : int
        ID of the spectrum to delete.
    """
    unwrap(client.delete(f"/api/spectrum/{spectrum_id}"))


def update_spectrum(
    client: httpx.Client,
    spectrum_id: int,
    payload: SpectrumUpdate,
) -> None:
    """Update a spectrum.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    spectrum_id : int
        ID of the spectrum to update.
    payload : SpectrumUpdate
        Fields to change. Omitted fields are left unchanged. ``group_ids``
        only ever adds groups (it never removes them) and accepts the
        string ``"all"`` to share with every group the token can access.
        Setting ``external_pi``, ``external_reducer`` or
        ``external_observer`` requires the matching ``pi``, ``reduced_by``
        or ``observed_by`` list of user IDs.
    """
    unwrap(
        client.put(
            f"/api/spectrum/{spectrum_id}",
            json=payload.model_dump(exclude_none=True),
        )
    )


def fetch_spectra_query(  # noqa: PLR0912, PLR0913 -- mirrors the query parameters
    client: httpx.Client,
    *,
    minimal_payload: bool = False,
    include_original_file: bool = False,
    obj_id: str | None = None,
    instrument_ids: list[int] | None = None,
    group_ids: list[int] | None = None,
    followup_request_ids: list[int] | None = None,
    assignment_ids: list[int] | None = None,
    origin: list[str] | None = None,
    label: list[str] | None = None,
    spectrum_type: list[str] | None = None,
    observed_before: str | None = None,
    observed_after: str | None = None,
    modified_before: str | None = None,
    modified_after: str | None = None,
    comments_filter: list[str] | None = None,
    comments_filter_author: list[str] | None = None,
    comments_filter_before: str | None = None,
    comments_filter_after: str | None = None,
) -> list[SpectrumDetailResponse]:
    """Query spectra across all sources, filtered on the server.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    minimal_payload : bool, optional
        Return only metadata for each spectrum (no wavelengths, fluxes,
        comments or annotations), which is much smaller.
    include_original_file : bool, optional
        Include the raw uploaded file in ``original_file_string``. Ignored
        when ``minimal_payload`` is set.
    obj_id : str, optional
        Partial match against the object ID a spectrum belongs to.
    instrument_ids, group_ids, followup_request_ids, assignment_ids : \
list of int, optional
        Restrict to spectra linked to any of these IDs.
    origin, label : list of str, optional
        Partial matches against the spectrum origin or label; a spectrum
        matches if any value matches.
    spectrum_type : list of str, optional
        Restrict to these spectrum types (the allowed types come from the
        server config, e.g. ``"source"`` or ``"host"``).
    observed_before, observed_after : str, optional
        Restrict by observation time; any date string the server can parse,
        e.g. ``"2020-01-01"``.
    modified_before, modified_after : str, optional
        Restrict by last-modified time, same format.
    comments_filter : list of str, optional
        Keep only spectra with a comment containing any of these strings.
    comments_filter_author : list of str, optional
        Only comments from these authors count towards ``comments_filter``.
    comments_filter_before, comments_filter_after : str, optional
        Only comments posted in this window count towards
        ``comments_filter``.
    """
    params: dict[str, str | bool] = {
        "minimalPayload": minimal_payload,
        "includeOriginalFile": include_original_file,
    }
    if obj_id is not None:
        params["objID"] = obj_id
    if instrument_ids is not None:
        params["instrumentIDs"] = ",".join(str(i) for i in instrument_ids)
    if group_ids is not None:
        params["groupIDs"] = ",".join(str(i) for i in group_ids)
    if followup_request_ids is not None:
        params["followupRequestIDs"] = ",".join(str(i) for i in followup_request_ids)
    if assignment_ids is not None:
        params["assignmentIDs"] = ",".join(str(i) for i in assignment_ids)
    if origin is not None:
        params["origin"] = ",".join(origin)
    if label is not None:
        params["label"] = ",".join(label)
    if spectrum_type is not None:
        params["type"] = ",".join(spectrum_type)
    if observed_before is not None:
        params["observedBefore"] = observed_before
    if observed_after is not None:
        params["observedAfter"] = observed_after
    if modified_before is not None:
        params["modifiedBefore"] = modified_before
    if modified_after is not None:
        params["modifiedAfter"] = modified_after
    if comments_filter is not None:
        params["commentsFilter"] = ",".join(comments_filter)
    if comments_filter_author is not None:
        params["commentsFilterAuthor"] = ",".join(comments_filter_author)
    if comments_filter_before is not None:
        params["commentsFilterBefore"] = comments_filter_before
    if comments_filter_after is not None:
        params["commentsFilterAfter"] = comments_filter_after
    response = client.get("/api/spectra", params=params)
    return [SpectrumDetailResponse.model_validate(item) for item in unwrap(response)]


def fetch_spectra_range(
    client: httpx.Client,
    *,
    instrument_ids: list[int] | None = None,
    min_date: str | None = None,
    max_date: str | None = None,
) -> list[SpectrumDetailResponse]:
    """Retrieve spectra observed within a date range.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    instrument_ids : list of int, optional
        Restrict to these instruments. If omitted, all instruments the
        token can see are included.
    min_date, max_date : str, optional
        Bounds on the observation time, as ISOT UTC strings, e.g.
        ``"2020-01-01T00:00:00"``. Either bound may be omitted to leave
        the range open ended.
    """
    params: dict[str, str | list[int]] = {}
    if instrument_ids is not None:
        params["instrument_ids"] = instrument_ids
    if min_date is not None:
        params["min_date"] = min_date
    if max_date is not None:
        params["max_date"] = max_date
    response = client.get("/api/spectra/range", params=params)
    return [SpectrumDetailResponse.model_validate(item) for item in unwrap(response)]


def post_spectra_bulk(  # noqa: PLR0913 -- mirrors the endpoint's body fields
    client: httpx.Client,
    *,
    group_id: int | None = None,
    obj_ids: list[str] | None = None,
    classifications: list[str] | None = None,
    classification_prob_threshold: float | None = None,
    max_sources: int | None = None,
) -> BulkSpectraResponse:
    """Retrieve slim spectra and phase anchors for a set of sources.

    Despite being a POST, this endpoint only reads data: it fans a whole
    source set into one response so that phase-stacked spectra views do not
    need one request per source.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    group_id : int, optional
        Restrict to sources saved to this group.
    obj_ids : list of str, optional
        Restrict to these object IDs.
    classifications : list of str, optional
        Restrict to sources carrying any of these non-machine-learning
        classifications.
    classification_prob_threshold : float, optional
        Only count classifications at or above this probability.
    max_sources : int, optional
        Maximum number of sources to fetch spectra for. Defaults to 200 on
        the server and is capped at 1000; at most 3000 spectra are
        returned, and ``truncated`` reports whether either cap was hit.
    """
    payload: dict[str, Any] = {}
    if group_id is not None:
        payload["group_id"] = group_id
    if obj_ids is not None:
        payload["obj_ids"] = obj_ids
    if classifications is not None:
        payload["classifications"] = classifications
    if classification_prob_threshold is not None:
        payload["classificationProbThreshold"] = classification_prob_threshold
    if max_sources is not None:
        payload["maxSources"] = max_sources
    response = client.post("/api/spectra/bulk", json=payload)
    return BulkSpectraResponse.model_validate(unwrap(response))


def parse_spectrum_ascii(
    client: httpx.Client,
    payload: SpectrumAsciiParse,
) -> ParsedSpectrumResponse:
    """Parse an ASCII spectrum without saving it to the database.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : SpectrumAsciiParse
        The ASCII file contents plus the column layout. The file must hold
        at least two columns and be smaller than 10MB; a leading ``#``
        header is parsed into ``altdata``. Column indices are 0-based and
        default to 0 for wavelengths and 1 for fluxes, with no error
        column. The returned spectrum has no ``id`` because nothing is
        persisted.
    """
    response = client.post(
        "/api/spectrum/parse/ascii",
        json=payload.model_dump(exclude_none=True),
    )
    return ParsedSpectrumResponse.model_validate(unwrap(response))


def post_spectrum_ascii(
    client: httpx.Client,
    payload: SpectrumAsciiPost,
) -> SpectrumPostResponse:
    """Upload a spectrum from an ASCII file.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : SpectrumAsciiPost
        The ASCII file contents, the object and instrument it belongs to,
        the observation time and the original ``filename`` (kept for
        bookkeeping). If ``group_ids`` is omitted, the server applies its
        default visibility; the string ``"all"`` shares the spectrum with
        the public group. Setting ``external_pi``, ``external_reducer`` or
        ``external_observer`` requires the matching ``pi``, ``reduced_by``
        or ``observed_by`` list of user IDs.
    """
    response = client.post(
        "/api/spectrum/ascii",
        json=payload.model_dump(exclude_none=True),
    )
    return SpectrumPostResponse.model_validate(unwrap(response))


def post_synthetic_photometry(
    client: httpx.Client,
    spectrum_id: int,
    filters: list[str],
) -> None:
    """Create synthetic photometry from a spectrum.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    spectrum_id : int
        ID of the spectrum to synthesise photometry from. Its ``units``
        must be set, otherwise the server cannot convert the fluxes.
    filters : list of str
        Bandpass names to compute AB magnitudes in. The resulting
        photometry points are saved for the spectrum's object and shared
        with every group the token can access.
    """
    unwrap(
        client.post(
            f"/api/spectra/synthphot/{spectrum_id}",
            json={"filters": filters},
        )
    )
