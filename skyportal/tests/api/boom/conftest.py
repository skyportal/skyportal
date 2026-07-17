"""Fixtures for BOOM integration tests.

These fixtures hit the live BOOM API (via SkyPortal's `@boom_available`
endpoints), so they require a running boom-api-1 service. Any test that
uses them will fail at fixture setup if BOOM is unreachable.
"""

import json
import os
import uuid

import pytest

from skyportal.tests import api

# Path inside the container written by the workflow's "Inject BOOM seed
# reference" step. Contains the objectId and candid of the first alert
# ingested by boom's consumer-ztf, so tests don't need to hard-code a
# specific OID that may not exist in the current seed dataset.
# We use /tmp because the skyportal-web-1 container runs as the
# `skyportal` user, which can't write under /skyportal/persistentdata
# directly (only its chowned subdirs).
_BOOM_SEED_FILE = "/tmp/boom_seed.json"


def pytest_configure(config):
    """Register custom markers so pytest doesn't warn about them."""
    config.addinivalue_line(
        "markers",
        "requires_boom_data: test depends on BOOM mongo being seeded "
        "(skipped automatically when no BOOM seed reference file is found).",
    )


def _load_boom_seed():
    """Return {objectId, candid} dict from the seed file, or None."""
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
    """Session-scoped (objectId, candid) for tests that need a real alert.

    Returns None if BOOM wasn't seeded (e.g. running locally without the
    workflow's seed step). Tests marked `requires_boom_data` will be
    skipped in that case by `_boom_seed_data_gate`.
    """
    return _load_boom_seed()


@pytest.fixture
def boom_seed_oid(boom_seed):
    if boom_seed is None:
        pytest.skip("BOOM seed file not present")
    return boom_seed["objectId"]


@pytest.fixture
def boom_seed_candid(boom_seed):
    if boom_seed is None:
        pytest.skip("BOOM seed file not present")
    return int(boom_seed["candid"])


@pytest.fixture
def boom_seed_ra(boom_seed):
    if boom_seed is None or boom_seed.get("ra") is None:
        pytest.skip("BOOM seed ra not present")
    return float(boom_seed["ra"])


@pytest.fixture
def boom_seed_dec(boom_seed):
    if boom_seed is None or boom_seed.get("dec") is None:
        pytest.skip("BOOM seed dec not present")
    return float(boom_seed["dec"])


@pytest.fixture(autouse=True)
def _boom_seed_data_gate(request):
    """Skip tests marked `requires_boom_data` when no seed file exists."""
    if "requires_boom_data" not in request.keywords:
        return
    if _load_boom_seed() is None:
        pytest.skip(
            f"BOOM seed reference {_BOOM_SEED_FILE} not present; "
            "the workflow's BOOM-seeding steps must run before these tests."
        )


@pytest.fixture
def boom_ztf_stream(super_admin_token, public_stream):
    """Decorate `public_stream` with ZTF_alerts altdata so that BOOM
    filters can be attached to it. BOOM derives the survey/permissions
    from `stream.altdata.collection` and `stream.altdata.selector`.
    """
    status, data = api(
        "PATCH",
        f"streams/{public_stream.id}",
        data={
            "name": str(uuid.uuid4()),
            "altdata": {"collection": "ZTF_alerts", "selector": [1, 2]},
        },
        token=super_admin_token,
    )
    assert status == 200, data
    return public_stream


@pytest.fixture
def boom_filter(super_admin_token, boom_ztf_stream, group_with_stream):
    """A SkyPortal Filter provisioned on the BOOM side.

    Two-step setup, mirroring the frontend:
      1. POST /filters to create the SkyPortal-side Filter (no altdata).
      2. POST /boom/filters/{id} which round-trips to BOOM, creates the
         BOOM filter, and populates Filter.altdata with the BOOM filter_id.

    Yields the SkyPortal Filter ID. Best-effort DELETE on teardown.

    BOOM validates new filters by running their pipeline against the ZTF
    corpus, so without seed data step 2 returns 400. We skip up-front
    when no seed reference file is present.
    """
    if _load_boom_seed() is None:
        pytest.skip(
            f"BOOM seed reference {_BOOM_SEED_FILE} not present; "
            "skip filter-provisioning tests until boom-mongo is seeded."
        )

    status, data = api(
        "POST",
        "filters",
        data={
            "name": str(uuid.uuid4()),
            "stream_id": boom_ztf_stream.id,
            "group_id": group_with_stream.id,
        },
        token=super_admin_token,
    )
    assert status == 200, data
    filter_id = data["data"]["id"]

    # BOOM rejects pipelines whose last stage isn't a $project that
    # includes objectId (validation in build_and_test_filter_version).
    pipeline = [
        {"$match": {"candidate.drb": {"$gt": 0.5}}},
        {"$project": {"objectId": 1, "candid": 1, "candidate": 1}},
    ]
    status, data = api(
        "POST",
        f"boom/filters/{filter_id}",
        data={
            "name": f"boom_filter_{filter_id}",
            "altdata": pipeline,
            "filters": "v1",
        },
        token=super_admin_token,
    )
    assert status == 200, data

    yield filter_id

    api("DELETE", f"boom/filters/{filter_id}", token=super_admin_token)


@pytest.fixture
def boom_filter_module_block(super_admin_token):
    """Insert a sample BOOM filter-module block into the MongoDB store.

    `BoomFilterModulesHandler` exposes no DELETE, so the block leaks; we
    use a UUID-suffixed name to avoid collisions across test runs.
    """
    name = f"test_block_{uuid.uuid4().hex[:8]}"
    payload = {
        "elements": "blocks",
        "data": {
            "block": {"$match": {"candidate.drb": {"$gt": 0.5}}},
            "streams": ["ZTF (1, 2)"],
        },
    }
    status, data = api(
        "POST",
        f"boom/filter_modules/{name}",
        data=payload,
        token=super_admin_token,
    )
    assert status == 200, data
    return name
