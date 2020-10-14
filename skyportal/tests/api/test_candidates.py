import uuid
import numpy.testing as npt
from skyportal.tests import api


def test_candidate_list(view_only_token, public_candidate):
    status, data = api("GET", "candidates", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"


def test_candidate_existence(view_only_token, public_candidate):
    status = api('HEAD', f'candidates/{public_candidate.id}', token=view_only_token)
    assert status == 200

    status = api(
        'HEAD', f'candidates/{public_candidate.id[:-1]}', token=view_only_token
    )
    assert status == 400


def test_token_user_retrieving_candidate(view_only_token, public_candidate):
    status, data = api(
        "GET", f"candidates/{public_candidate.id}", token=view_only_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(k in data["data"] for k in ["ra", "dec", "redshift", "dm"])


def test_token_user_update_candidate(manage_sources_token, public_candidate):
    status, data = api(
        "PATCH",
        f"candidates/{public_candidate.id}",
        data={"ra": 234.22, "redshift": 3, "transient": False, "ra_dis": 2.3},
        token=manage_sources_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"candidates/{public_candidate.id}", token=manage_sources_token
    )
    assert status == 200
    assert data["status"] == "success"
    npt.assert_almost_equal(data["data"]["ra"], 234.22)
    npt.assert_almost_equal(data["data"]["redshift"], 3.0)


def test_cannot_update_candidate_without_permission(view_only_token, public_candidate):
    status, data = api(
        "PATCH",
        f"candidates/{public_candidate.id}",
        data={
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
        },
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_token_user_post_new_candidate(
    upload_data_token, view_only_token, public_filter
):
    candidate_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": candidate_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == candidate_id

    status, data = api("GET", f"candidates/{candidate_id}", token=view_only_token)
    assert status == 200
    assert data["data"]["id"] == candidate_id
    npt.assert_almost_equal(data["data"]["ra"], 234.22)


def test_cannot_add_candidate_without_filter_id(upload_data_token):
    candidate_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": candidate_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
        },
        token=upload_data_token,
    )
    assert status == 400
