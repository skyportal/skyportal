"""Shared fixtures for skyportal-py tests."""

from __future__ import annotations

import pytest

from skyportal_py import SkyPortal, create_client

BASE_URL = "https://skyportal.example.com"


@pytest.fixture
def client() -> SkyPortal:
    """Return a client pointed at a fake instance."""
    return create_client(BASE_URL, token="abc123")
