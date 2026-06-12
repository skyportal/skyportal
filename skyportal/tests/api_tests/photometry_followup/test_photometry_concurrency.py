"""Concurrent-write stress tests for the photometry endpoints.

These tests exercise the photometry POST/PUT handlers under genuine
concurrent traffic. They are the regression coverage for the
ON-CONFLICT-based dedup machinery that replaced the old LOCK TABLE
serialization in `bulk_upsert_photometry` / `insert_new_photometry_data`.

Unlike the rest of the photometry test suite — where each test is a
single-actor sequential script on uuid-namespaced rows — these tests
deliberately have N HTTP clients race on the *same* dedup tuple
(obj_id, instrument_id, mjd, filter, origin, flux, fluxerr) so that the
ON-CONFLICT DO NOTHING / DO UPDATE paths actually fire under contention.

Concurrency is provided by `concurrent.futures.ThreadPoolExecutor`
calling the test client's `api(...)` helper. The test server is the
same single-process tornado supervisor the rest of the suite uses, so
"concurrent" here means multiple HTTP requests in flight against the
same backend at the same time.
"""

import uuid
from concurrent.futures import ThreadPoolExecutor

from skyportal.tests import api

N_WORKERS = 8


def _post_photometry(token, payload):
    """Single POST call returning (status, response_json)."""
    return api("POST", "photometry", data=payload, token=token)


def _put_photometry(token, payload):
    """Single PUT call returning (status, response_json)."""
    return api("PUT", "photometry", data=payload, token=token)


def test_concurrent_post_identical_dedup_key(
    upload_data_token, public_source, public_group, ztf_camera
):
    """N concurrent POSTs of an identical photometry row.

    All N requests carry the same (obj_id, mjd, filter, origin, flux,
    fluxerr) tuple. ON-CONFLICT DO NOTHING in `bulk_upsert_photometry`
    should ensure:

    - Exactly one row is created in the DB.
    - At most one worker sees a 200 success; the rest see a 400
      "already exists" error (the POST handler's `duplicates="error"`
      mode is the default).
    - No worker sees a 500 (no IntegrityError leaks through).
    """
    payload = {
        "obj_id": str(public_source.id),
        "instrument_id": ztf_camera.id,
        "mjd": [59500.0],
        "mag": [19.5],
        "magerr": [0.05],
        "limiting_mag": [21.0],
        "magsys": ["ab"],
        "filter": ["ztfr"],
        "ra": [42.0],
        "dec": [-22.0],
        "origin": [f"concurrency-test-{uuid.uuid4()}"],
        "group_ids": [public_group.id],
    }

    with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
        futures = [
            pool.submit(_post_photometry, upload_data_token, payload)
            for _ in range(N_WORKERS)
        ]
        results = [f.result() for f in futures]

    statuses = [s for s, _ in results]

    assert all(s in (200, 400) for s in statuses), (
        f"unexpected status codes: {statuses}"
    )
    assert 500 not in statuses, "handler 5xx'd under contention"

    successes = [data for s, data in results if s == 200]
    errors = [data for s, data in results if s == 400]

    assert len(successes) <= 1, (
        f"expected at most one POST to succeed, got {len(successes)}; "
        f"first success: {successes[0] if successes else None}"
    )
    assert len(errors) == N_WORKERS - len(successes)

    # The error responses should mention "already exists" (the dedup
    # message), not some other 400. If a worker is racing on a different
    # kind of validation failure, this catches it.
    for err in errors:
        assert (
            "already exists" in str(err).lower() or "duplicate" in str(err).lower()
        ), f"unexpected 400 body: {err}"

    # End state: exactly one photometry row for this origin tag exists.
    status, get_data = api(
        "GET",
        f"sources/{public_source.id}",
        params={"includePhotometry": "true"},
        token=upload_data_token,
    )
    assert status == 200
    matching = [
        p
        for p in get_data["data"]["photometry"]
        if p.get("origin") == payload["origin"][0]
    ]
    assert len(matching) == 1, (
        f"expected exactly 1 row for this origin, found {len(matching)}"
    )


def test_concurrent_put_ignore_flux_overwrite_flux(
    super_admin_token, upload_data_token, public_source, public_group, ztf_camera
):
    """N concurrent PUTs with duplicate_ignore_flux=True&overwrite_flux=True.

    This is the photometry endpoint's "overwrite the existing row's flux"
    path. Dedup ignores flux/fluxerr; on a duplicate hit, the handler
    mutates the existing row's flux in place and attaches any new
    group/stream memberships.

    Under concurrent traffic, the original implementation used ORM
    collection assignment (`duplicate.groups = groups`) for the group
    attach on the duplicate branch — which emits plain INSERTs into
    `group_photometry` that race on the unique
    `(group_id, photometr_id)` index. N-1 workers would hit
    `psycopg.errors.UniqueViolation` → 400. This test is the regression
    coverage for the fix: an explicit
    `pg_insert(GroupPhotometry).on_conflict_do_nothing(...)`.

    Invariants:

    - All workers see 200. No 500s.
    - The seed POST creates exactly one row; after the concurrent PUTs,
      still exactly one row (no torn-state dedup miss).
    - That row's final mag corresponds to one of the submitted mags
      (some PUT actually won the race; the seed value didn't survive
      unchanged through all N updates).

    Note: duplicate_ignore_flux=True is a super-admin-only feature, so
    we use super_admin_token here.
    """
    origin = f"concurrency-put-{uuid.uuid4()}"
    mjd = 59600.0

    # Seed: create the row that the concurrent PUTs will then update.
    seed_payload = {
        "obj_id": str(public_source.id),
        "instrument_id": ztf_camera.id,
        "mjd": [mjd],
        "mag": [19.0],
        "magerr": [0.05],
        "limiting_mag": [21.0],
        "magsys": ["ab"],
        "filter": ["ztfr"],
        "ra": [42.0],
        "dec": [-22.0],
        "origin": [origin],
        "group_ids": [public_group.id],
    }
    status, data = api("POST", "photometry", data=seed_payload, token=upload_data_token)
    assert status == 200, f"seed POST failed: {data}"

    # Each worker submits a distinct mag at the same (mjd, filter, origin).
    mags_in = [20.0 + 0.1 * i for i in range(N_WORKERS)]

    def _put_with_mag(mag):
        payload = {**seed_payload, "mag": [mag]}
        return api(
            "PUT",
            "photometry?duplicate_ignore_flux=True&overwrite_flux=True",
            data=payload,
            token=super_admin_token,
        )

    with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
        results = list(pool.map(_put_with_mag, mags_in))

    statuses = [s for s, _ in results]
    errors = [data for s, data in results if s != 200]
    assert all(s == 200 for s in statuses), (
        f"PUT should not error under contention, got statuses: {statuses}; "
        f"sample error body: {errors[0] if errors else None}"
    )

    status, get_data = api(
        "GET",
        f"sources/{public_source.id}",
        params={"includePhotometry": "true"},
        token=upload_data_token,
    )
    assert status == 200
    matching = [p for p in get_data["data"]["photometry"] if p.get("origin") == origin]
    assert len(matching) == 1, (
        f"expected exactly 1 row for this origin after concurrent "
        f"ignore_flux+overwrite_flux PUTs, found {len(matching)} "
        "(dedup pre-check race?)"
    )
    final_mag = matching[0]["mag"]
    # The final mag must be one of the submitted values (a real winner
    # of the race), not the seed mag (which would mean ALL updates were
    # lost) and not something corrupt.
    assert final_mag in mags_in, (
        f"final mag {final_mag} is neither one of the concurrent inputs "
        f"{mags_in} nor a plausible torn value; likely a lost-update bug"
    )
    assert final_mag != 19.0, (
        "final mag still equals the seed value — all concurrent updates were lost"
    )


def test_concurrent_post_disjoint_keys(
    upload_data_token, public_source, public_group, ztf_camera
):
    """N concurrent POSTs on disjoint dedup keys.

    Sanity check: the contention machinery (ON-CONFLICT, transactional
    ordering) shouldn't be slowing down or incorrectly serializing
    requests that don't actually share a key. All N requests should
    succeed and produce N distinct rows.
    """
    base_mjd = 59700.0

    def _post_at_offset(i):
        payload = {
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [base_mjd + i],
            "mag": [19.5],
            "magerr": [0.05],
            "limiting_mag": [21.0],
            "magsys": ["ab"],
            "filter": ["ztfr"],
            "ra": [42.0],
            "dec": [-22.0],
            "origin": [f"disjoint-{uuid.uuid4()}"],
            "group_ids": [public_group.id],
        }
        return api("POST", "photometry", data=payload, token=upload_data_token)

    with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
        results = list(pool.map(_post_at_offset, range(N_WORKERS)))

    statuses = [s for s, _ in results]
    assert all(s == 200 for s in statuses), (
        f"disjoint POSTs should all succeed, got: {statuses}"
    )

    inserted_ids = {data["data"]["ids"][0] for _, data in results}
    assert len(inserted_ids) == N_WORKERS, (
        f"expected {N_WORKERS} distinct row IDs, got {len(inserted_ids)} "
        "(some inserts may have collided)"
    )
