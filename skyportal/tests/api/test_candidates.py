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


def test_candidate_list_sorting_basic(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    status, data = api(
        "POST",
        "annotation",
        data={
            "obj_id": public_candidate.id,
            "origin": origin,
            "data": {"numeric_field": 1},
        },
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "annotation",
        data={
            "obj_id": public_candidate2.id,
            "origin": origin,
            "data": {"numeric_field": 2},
        },
        token=annotation_token,
    )
    assert status == 200

    # Sort by the numeric field so that public_candidate is returned first,
    # instead of by last_detected (which would put public_candidate2 first)
    status, data = api(
        "GET",
        f"candidates/?sortByAnnotationOrigin={origin}&sortByAnnotationKey=numeric_field",
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["candidates"][0]["id"] == public_candidate.id
    assert data["data"]["candidates"][1]["id"] == public_candidate2.id


def test_candidate_list_sorting_different_origins(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    origin2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "annotation",
        data={
            "obj_id": public_candidate.id,
            "origin": origin,
            "data": {"numeric_field": 1},
        },
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "annotation",
        data={
            "obj_id": public_candidate2.id,
            "origin": origin2,
            "data": {"numeric_field": 2},
        },
        token=annotation_token,
    )
    assert status == 200

    # If just sorting on numeric_field, public_candidate should be returned first
    # but since we specify origin2 (which is not the origin for the
    # public_candidate annotation) public_candidate2 is returned first
    status, data = api(
        "GET",
        f"candidates/?sortByAnnotationOrigin={origin2}&sortByAnnotationKey=numeric_field",
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["candidates"][0]["id"] == public_candidate2.id
    assert data["data"]["candidates"][1]["id"] == public_candidate.id


def test_candidate_list_sorting_hidden_group(
    annotation_token_two_groups,
    view_only_token,
    public_candidate_two_groups,
    public_candidate2,
    public_group2,
):
    # Post an annotation that belongs only to public_group2 (not allowed for view_only_token)
    status, data = api(
        "POST",
        "annotation",
        data={
            "obj_id": public_candidate_two_groups.id,
            "origin": f"{public_group2.id}",
            "data": {"numeric_field": 1},
            "group_ids": [public_group2.id],
        },
        token=annotation_token_two_groups,
    )
    assert status == 200

    # This one belongs to both public groups and is thus visible
    status, data = api(
        "POST",
        "annotation",
        data={
            "obj_id": public_candidate2.id,
            "origin": f"{public_group2.id}",
            "data": {"numeric_field": 2},
        },
        token=annotation_token_two_groups,
    )
    assert status == 200

    # Sort by the numeric field ascending, but since view_only_token does not
    # have access to public_group2, the first annotation above should not be
    # seen in the response
    status, data = api(
        "GET",
        f"candidates/?sortByAnnotationOrigin={public_group2.id}&sortByAnnotationKey=numeric_field",
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["candidates"][0]["id"] == public_candidate_two_groups.id
    assert data["data"]["candidates"][0]["annotations"] == []
    assert data["data"]["candidates"][1]["id"] == public_candidate2.id


def test_candidate_list_sorting_null_value(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    status, data = api(
        "POST",
        "annotation",
        data={
            "obj_id": public_candidate.id,
            "origin": origin,
            "data": {"numeric_field": 1},
        },
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "annotation",
        data={
            "obj_id": public_candidate2.id,
            "origin": origin,
            "data": {"some_other_field": 2},
        },
        token=annotation_token,
    )
    assert status == 200

    # The second candidate does not have "numeric_field" in the annotations, and
    # should thus show up after the first candidate, even though it was posted
    # latest
    status, data = api(
        "GET",
        f"candidates/?sortByAnnotationOrigin={origin}&sortByAnnotationKey=numeric_field",
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["candidates"][0]["id"] == public_candidate.id
    assert data["data"]["candidates"][1]["id"] == public_candidate2.id
