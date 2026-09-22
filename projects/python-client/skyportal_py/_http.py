"""Internal envelope unwrapping and error handling."""

from __future__ import annotations

from typing import Any

import httpx


class _Unset:
    """Sentinel distinguishing "argument not provided" from an explicit None."""

    def __repr__(self) -> str:
        return "UNSET"


UNSET: Any = _Unset()


class SkyPortalError(Exception):
    """Raised when the SkyPortal API returns an error response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def unwrap(response: httpx.Response) -> Any:  # noqa: ANN401
    """Return the ``data`` field of a SkyPortal response envelope.

    Raises
    ------
    SkyPortalError
        If the response is an error envelope or not JSON.
    """
    try:
        payload = response.json()
    except ValueError:
        message = (
            f"SkyPortal returned a non-JSON response (HTTP {response.status_code})"
        )
        raise SkyPortalError(message, response.status_code) from None

    if response.is_success and payload.get("status") == "success":
        return payload.get("data")

    message = payload.get("message") or f"HTTP {response.status_code}"
    raise SkyPortalError(message, response.status_code)


def unwrap_content(response: httpx.Response) -> bytes:
    """Return the raw body of a binary SkyPortal response.

    Endpoints that return a file (plots, skymaps, finding charts) send bytes
    rather than a JSON envelope, so their errors are unwrapped separately.

    Raises
    ------
    SkyPortalError
        If the response is an error response.
    """
    if response.is_success:
        return response.content

    try:
        message = response.json().get("message") or f"HTTP {response.status_code}"
    except ValueError:
        message = f"HTTP {response.status_code}"
    raise SkyPortalError(message, response.status_code)
