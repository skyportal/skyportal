"""Typed endpoint functions for ``/api/analysis_service`` and ``/api/obj/analysis``."""

from __future__ import annotations

from typing import Any

import httpx
from skyportal_py_models.analysis import (
    AnalysisInputType,
    AnalysisPost,
    AnalysisPostResponse,
    AnalysisServicePost,
    AnalysisServicePostResponse,
    AnalysisServiceResponse,
    AnalysisServiceUpdate,
    AnalysisType,
    AnalysisUploadPost,
    AnalysisUploadResponse,
    AuthenticationType,
    DefaultAnalysisPost,
    DefaultAnalysisPostResponse,
    DefaultAnalysisResponse,
    ObjAnalysisResponse,
    WebhookStatus,
)

from skyportal_py._http import unwrap, unwrap_content

__all__ = [
    "AnalysisInputType",
    "AnalysisPost",
    "AnalysisPostResponse",
    "AnalysisServicePost",
    "AnalysisServicePostResponse",
    "AnalysisServiceResponse",
    "AnalysisServiceUpdate",
    "AnalysisType",
    "AnalysisUploadPost",
    "AnalysisUploadResponse",
    "AuthenticationType",
    "DefaultAnalysisPost",
    "DefaultAnalysisPostResponse",
    "DefaultAnalysisResponse",
    "ObjAnalysisResponse",
    "WebhookStatus",
]


def fetch_analysis_service(
    client: httpx.Client,
    analysis_service_id: int,
) -> AnalysisServiceResponse:
    """Retrieve a single analysis service by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_service_id : int
        ID of the analysis service.
    """
    response = client.get(f"/api/analysis_service/{analysis_service_id}")
    return AnalysisServiceResponse.model_validate(unwrap(response))


def fetch_analysis_services(client: httpx.Client) -> list[AnalysisServiceResponse]:
    """Retrieve all analysis services visible to the token.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    """
    response = client.get("/api/analysis_service")
    return [
        AnalysisServiceResponse.model_validate(service) for service in unwrap(response)
    ]


def post_analysis_service(
    client: httpx.Client,
    payload: AnalysisServicePost,
) -> AnalysisServicePostResponse:
    """Register a new analysis service.

    Requires the "Manage Analysis Services" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    payload : AnalysisServicePost
        The service to register. ``optional_analysis_parameters`` and
        ``authinfo`` (sent as ``_authinfo``) must be JSON-encoded strings;
        ``authinfo`` is required unless ``authentication_type`` is
        ``"none"``. If ``group_ids`` is omitted, the service is made
        accessible to all of the token's groups.
    """
    response = client.post(
        "/api/analysis_service",
        json=payload.model_dump(by_alias=True, exclude_none=True),
    )
    return AnalysisServicePostResponse.model_validate(unwrap(response))


def update_analysis_service(
    client: httpx.Client,
    analysis_service_id: int,
    payload: AnalysisServiceUpdate,
) -> None:
    """Update an analysis service.

    Only the provided fields are sent; omitted fields are left unchanged.
    Requires the "Manage Analysis Services" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_service_id : int
        ID of the analysis service to update.
    payload : AnalysisServiceUpdate
        The fields to update.
    """
    unwrap(
        client.patch(
            f"/api/analysis_service/{analysis_service_id}",
            json=payload.model_dump(exclude_none=True),
        )
    )


def delete_analysis_service(client: httpx.Client, analysis_service_id: int) -> None:
    """Delete an analysis service.

    Requires the "Manage Analysis Services" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_service_id : int
        ID of the analysis service to delete.
    """
    unwrap(client.delete(f"/api/analysis_service/{analysis_service_id}"))


def fetch_default_analysis(
    client: httpx.Client,
    analysis_service_id: int,
    default_analysis_id: int,
) -> DefaultAnalysisResponse:
    """Retrieve a single default analysis by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_service_id : int
        ID of the analysis service the default analysis belongs to.
    default_analysis_id : int
        ID of the default analysis.
    """
    response = client.get(
        f"/api/analysis_service/{analysis_service_id}"
        f"/default_analysis/{default_analysis_id}"
    )
    return DefaultAnalysisResponse.model_validate(unwrap(response))


def fetch_default_analyses(
    client: httpx.Client,
    analysis_service_id: int,
) -> list[DefaultAnalysisResponse]:
    """Retrieve the default analyses of an analysis service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_service_id : int
        ID of the analysis service.
    """
    response = client.get(
        f"/api/analysis_service/{analysis_service_id}/default_analysis"
    )
    return [
        DefaultAnalysisResponse.model_validate(default) for default in unwrap(response)
    ]


def post_default_analysis(
    client: httpx.Client,
    analysis_service_id: int,
    payload: DefaultAnalysisPost,
) -> DefaultAnalysisPostResponse:
    """Create a default analysis for an analysis service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_service_id : int
        ID of the analysis service to attach the default analysis to.
    payload : DefaultAnalysisPost
        The default analysis to create. ``daily_limit`` defaults to 10 and
        must be between 1 and 1000. If ``group_ids`` is omitted, the server
        uses all of the token's groups.
    """
    response = client.post(
        f"/api/analysis_service/{analysis_service_id}/default_analysis",
        json=payload.model_dump(exclude_none=True),
    )
    return DefaultAnalysisPostResponse.model_validate(unwrap(response))


def update_default_analysis(
    client: httpx.Client,
    analysis_service_id: int,
    default_analysis_id: int,
    payload: DefaultAnalysisPost,
) -> None:
    """Update a default analysis.

    Only the provided fields are sent; omitted fields are left unchanged.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_service_id : int
        ID of the analysis service the default analysis belongs to.
    default_analysis_id : int
        ID of the default analysis to update.
    payload : DefaultAnalysisPost
        The fields to update.
    """
    unwrap(
        client.patch(
            f"/api/analysis_service/{analysis_service_id}"
            f"/default_analysis/{default_analysis_id}",
            json=payload.model_dump(exclude_none=True),
        )
    )


def delete_default_analysis(
    client: httpx.Client,
    analysis_service_id: int,
    default_analysis_id: int,
) -> None:
    """Delete a default analysis.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_service_id : int
        ID of the analysis service the default analysis belongs to.
    default_analysis_id : int
        ID of the default analysis to delete.
    """
    unwrap(
        client.delete(
            f"/api/analysis_service/{analysis_service_id}"
            f"/default_analysis/{default_analysis_id}"
        )
    )


def post_analysis(
    client: httpx.Client,
    obj_id: str,
    analysis_service_id: int,
    payload: AnalysisPost | None = None,
) -> AnalysisPostResponse:
    """Start an analysis run on an object.

    Requires the "Run Analyses" permission. The server assembles the input
    data, calls the external service asynchronously, and returns the new
    analysis ID immediately; poll :func:`fetch_analysis` for the status.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID to analyze.
    analysis_service_id : int
        ID of the analysis service to run. Must not be an upload-only
        service (use :func:`post_analysis_upload` for those).
    payload : AnalysisPost, optional
        Run options. ``analysis_parameters`` keys must be declared by the
        service's ``optional_analysis_parameters``. If ``group_ids`` is
        omitted, results are visible to all of the token's groups.
    """
    body = payload.model_dump(exclude_none=True) if payload is not None else {}
    response = client.post(
        f"/api/obj/{obj_id}/analysis/{analysis_service_id}", json=body
    )
    return AnalysisPostResponse.model_validate(unwrap(response))


def fetch_analysis(
    client: httpx.Client,
    analysis_id: int,
    *,
    include_analysis_data: bool = False,
    include_filename: bool = False,
) -> ObjAnalysisResponse:
    """Retrieve a single analysis by ID.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_id : int
        ID of the analysis.
    include_analysis_data : bool, optional
        Include the analysis data in the response; can be large.
    include_filename : bool, optional
        Include the server-side filename of the analysis data.
    """
    response = client.get(
        f"/api/obj/analysis/{analysis_id}",
        params={
            "includeAnalysisData": include_analysis_data,
            "includeFilename": include_filename,
        },
    )
    return ObjAnalysisResponse.model_validate(unwrap(response))


def fetch_analyses(
    client: httpx.Client,
    *,
    obj_id: str | None = None,
    analysis_service_id: int | None = None,
    summary_only: bool = False,
    include_filename: bool = False,
) -> list[ObjAnalysisResponse]:
    """Retrieve analyses, optionally restricted to one object.

    Without ``obj_id``, the server returns a minimal record per analysis
    (IDs, status, and timestamps only).

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str, optional
        Restrict to analyses whose object ID contains this string.
    analysis_service_id : int, optional
        Restrict to analyses run with this analysis service.
    summary_only : bool, optional
        Only return analyses from services with ``is_summary`` set.
    include_filename : bool, optional
        Include the server-side filename of the analysis data. Only
        applies when ``obj_id`` is provided.
    """
    params: dict[str, str | int | bool] = {
        "summaryOnly": summary_only,
        "includeFilename": include_filename,
    }
    if obj_id is not None:
        params["objID"] = obj_id
    if analysis_service_id is not None:
        params["analysisServiceID"] = analysis_service_id
    response = client.get("/api/obj/analysis", params=params)
    return [
        ObjAnalysisResponse.model_validate(analysis) for analysis in unwrap(response)
    ]


def delete_analysis(client: httpx.Client, analysis_id: int) -> None:
    """Delete an analysis and its stored data.

    Requires the "Run Analyses" permission.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_id : int
        ID of the analysis to delete.
    """
    unwrap(client.delete(f"/api/obj/analysis/{analysis_id}"))


def post_analysis_upload(
    client: httpx.Client,
    obj_id: str,
    analysis_service_id: int,
    payload: AnalysisUploadPost,
) -> AnalysisUploadResponse:
    """Upload results for an upload-only analysis service.

    Requires the "Run Analyses" permission. The analysis is stored as
    completed without calling any external service.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    obj_id : str
        Object ID the analysis belongs to.
    analysis_service_id : int
        ID of the analysis service; must be an upload-only service.
    payload : AnalysisUploadPost
        The results to store. ``analysis`` holds the results data (e.g.
        ``{"results": ...}``); ``message`` becomes the status message. If
        ``group_ids`` is omitted, results are visible to all of the
        token's groups.
    """
    response = client.post(
        f"/api/obj/{obj_id}/analysis_upload/{analysis_service_id}",
        json=payload.model_dump(exclude_none=True),
    )
    return AnalysisUploadResponse.model_validate(unwrap(response))


def fetch_analysis_results(
    client: httpx.Client,
    analysis_id: int,
    *,
    download: bool = False,
) -> Any:  # noqa: ANN401
    """Retrieve the results data of a completed analysis.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_id : int
        ID of the analysis.
    download : bool, optional
        Retrieve the results as a JSON file download instead of the usual
        response envelope; the return value is then the raw file bytes.
    """
    response = client.get(
        f"/api/obj/analysis/{analysis_id}/results",
        params={"download": "true"} if download else {},
    )
    if download:
        return unwrap_content(response)
    return unwrap(response)


def fetch_analysis_plot(
    client: httpx.Client,
    analysis_id: int,
    *,
    plot_number: int = 0,
) -> bytes:
    """Download one plot produced by an analysis.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    analysis_id : int
        ID of the analysis.
    plot_number : int, optional
        Which plot to download, starting at 0. The number of available
        plots is the ``num_plots`` field of :func:`fetch_analysis`.
    """
    response = client.get(f"/api/obj/analysis/{analysis_id}/plots/{plot_number}")
    return unwrap_content(response)
