"""Typed endpoint functions for ``/api/weather``."""

from __future__ import annotations

import httpx
from skyportal_py_models.weather import WeatherResponse

from skyportal_py._http import unwrap

__all__ = [
    "WeatherResponse",
]


def fetch_weather(
    client: httpx.Client,
    *,
    telescope_id: int | None = None,
) -> WeatherResponse:
    """Retrieve the weather at a telescope site.

    The server refreshes the cached OpenWeather data only once the configured
    refresh interval has elapsed, and reports upstream failures in
    ``message`` rather than as an error. When no telescope can be resolved at
    all, every field except ``weather`` is absent.

    Parameters
    ----------
    client : httpx.Client
        Client from :func:`skyportal_py.create_client`.
    telescope_id : int, optional
        TelescopeResponse to report on. If omitted the server falls back to the user's
        weather preference, then to the first telescope the token can access.
    """
    params: dict[str, int] = {}
    if telescope_id is not None:
        params["telescope_id"] = telescope_id
    response = client.get("/api/weather", params=params)
    return WeatherResponse.model_validate(unwrap(response))
