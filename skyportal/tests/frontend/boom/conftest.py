"""Frontend test fixtures for BOOM integration tests.

These tests use skyportal's session-scoped Playwright `page` fixture (defined in
skyportal/tests/test_util.py and re-exported via skyportal/tests/conftest.py)
to drive a headless Firefox against the running fritz/skyportal app.

The seed-file probe is duplicated from the api/boom/conftest.py because
pytest's conftest discovery doesn't cross sibling test trees — these
frontend tests are at tests/frontend/boom/, the api ones at tests/api/boom/.
"""

import json
import os

import pytest

_BOOM_SEED_FILE = "/tmp/boom_seed.json"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_boom_data: test depends on BOOM mongo being seeded "
        "(skipped automatically when no BOOM seed reference file is found).",
    )


def _load_boom_seed():
    if not os.path.exists(_BOOM_SEED_FILE):
        return None
    try:
        with open(_BOOM_SEED_FILE) as f:
            payload = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if "objectId" not in payload or "candid" not in payload:
        return None
    return payload


@pytest.fixture(scope="session")
def boom_seed():
    return _load_boom_seed()


@pytest.fixture
def boom_seed_oid(boom_seed):
    if boom_seed is None:
        pytest.skip("BOOM seed file not present")
    return boom_seed["objectId"]


@pytest.fixture(autouse=True)
def _boom_seed_data_gate(request):
    if "requires_boom_data" not in request.keywords:
        return
    if _load_boom_seed() is None:
        pytest.skip(
            f"BOOM seed reference {_BOOM_SEED_FILE} not present; "
            "the workflow's BOOM-seeding steps must run before these tests."
        )
