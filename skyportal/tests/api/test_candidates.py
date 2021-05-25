import time
import datetime
import uuid
import numpy.testing as npt

from skyportal.tests import api

from tdtax import taxonomy, __version__


def test_candidate_list(view_only_token, public_candidate):
    status, data = api("GET", "candidates", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"


def test_candidate_existence(view_only_token, public_candidate):
    status, _ = api("HEAD", f"candidates/{public_candidate.id}", token=view_only_token)
    assert status == 200

    status, _ = api(
        "HEAD", f"candidates/{public_candidate.id[:-1]}", token=view_only_token
    )
    assert status == 404


def test_token_user_retrieving_candidate(view_only_token, public_candidate):
    status, data = api(
        "GET", f"candidates/{public_candidate.id}", token=view_only_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(k in data["data"] for k in ["ra", "dec", "redshift", "dm"])
    assert "photometry" not in data["data"]


def test_token_user_retrieving_candidate_with_phot(view_only_token, public_candidate):
    status, data = api(
        "GET",
        f"candidates/{public_candidate.id}?includePhotometry=true",
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(k in data["data"] for k in ["ra", "dec", "redshift", "dm", "photometry"])


def test_token_user_retrieving_candidate_with_spec(view_only_token, public_candidate):
    status, data = api(
        "GET",
        f"candidates/{public_candidate.id}?includeSpectra=true",
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(k in data["data"] for k in ["ra", "dec", "redshift", "dm", "spectra"])


def test_token_user_post_delete_new_candidate(
    upload_data_token,
    view_only_token,
    public_filter,
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api("GET", f"candidates/{obj_id}", token=view_only_token)
    assert status == 200
    assert data["data"]["id"] == obj_id
    npt.assert_almost_equal(data["data"]["ra"], 234.22)

    status, data = api(
        "DELETE",
        f"candidates/{obj_id}/{public_filter.id}",
        token=upload_data_token,
    )
    assert status == 200


def test_cannot_add_candidate_without_filter_id(upload_data_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 400


def test_cannot_add_candidate_without_passed_at(upload_data_token, public_filter):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
        },
        token=upload_data_token,
    )
    assert status == 400


def test_token_user_post_two_candidates_same_obj_filter(
    upload_data_token, view_only_token, public_filter
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api("GET", f"candidates/{obj_id}", token=view_only_token)
    assert status == 200
    assert data["data"]["id"] == obj_id
    npt.assert_almost_equal(data["data"]["ra"], 234.22)

    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200


def test_token_user_cannot_post_two_candidates_same_obj_filter_passed_at(
    upload_data_token, view_only_token, public_filter
):
    obj_id = str(uuid.uuid4())
    passed_at = str(datetime.datetime.utcnow())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": passed_at,
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api("GET", f"candidates/{obj_id}", token=view_only_token)
    assert status == 200
    assert data["data"]["id"] == obj_id
    npt.assert_almost_equal(data["data"]["ra"], 234.22)

    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": passed_at,
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
    # instead of by last_detected_at (which would put public_candidate2 first)
    status, data = api(
        "GET",
        "candidates",
        params={
            "sortByAnnotationOrigin": f"{origin}",
            "sortByAnnotationKey": "numeric_field",
        },
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
        "candidates",
        params={
            "sortByAnnotationOrigin": f"{origin2}",
            "sortByAnnotationKey": "numeric_field",
        },
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
        "candidates",
        params={
            "sortByAnnotationOrigin": f"{public_group2.id}",
            "sortByAnnotationKey": "numeric_field",
        },
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
        "candidates",
        params={
            "sortByAnnotationOrigin": f"{origin}",
            "sortByAnnotationKey": "numeric_field",
        },
        token=view_only_token,
    )

    assert status == 200
    assert data["data"]["candidates"][0]["id"] == public_candidate.id
    assert data["data"]["candidates"][1]["id"] == public_candidate2.id


def test_candidate_list_filtering_numeric(
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

    # Filter by the numeric field with max value 1.5 so that only public_candidate
    # is returned
    status, data = api(
        "GET",
        "candidates",
        params={
            "annotationFilterList": f'{{"origin":"{origin}","key":"numeric_field","min":0,"max":1.5}}',
        },
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["candidates"]) == 1
    assert data["data"]["candidates"][0]["id"] == public_candidate.id


def test_candidate_list_filtering_boolean(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    status, data = api(
        "POST",
        "annotation",
        data={
            "obj_id": public_candidate.id,
            "origin": origin,
            "data": {"bool_field": True},
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
            "data": {"bool_field": False},
        },
        token=annotation_token,
    )
    assert status == 200

    # Filter by the numeric field with value == true so that only public_candidate
    # is returned
    status, data = api(
        "GET",
        "candidates",
        params={
            "annotationFilterList": f'{{"origin": "{origin}", "key": "bool_field", "value": "true"}}',
        },
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["candidates"]) == 1
    assert data["data"]["candidates"][0]["id"] == public_candidate.id


def test_candidate_list_filtering_string(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    status, data = api(
        "POST",
        "annotation",
        data={
            "obj_id": public_candidate.id,
            "origin": origin,
            "data": {"string_field": "a"},
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
            "data": {"string_field": "b"},
        },
        token=annotation_token,
    )
    assert status == 200

    # Filter by the numeric field with value == "a" so that only public_candidate
    # is returned
    status, data = api(
        "GET",
        "candidates",
        params={
            "annotationFilterList": f'{{"origin": "{origin}", "key": "string_field", "value": "a"}}',
        },
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["candidates"]) == 1
    assert data["data"]["candidates"][0]["id"] == public_candidate.id


def test_candidate_list_classifications(
    upload_data_token,
    taxonomy_token,
    classification_token,
    view_only_token,
    public_filter,
    public_group,
):
    # Post a candidate with a classification, and one without
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id1},
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        'POST',
        'taxonomy',
        data={
            'name': "test taxonomy" + str(uuid.uuid4()),
            'hierarchy': taxonomy,
            'group_ids': [public_group.id],
            'provenance': f"tdtax_{__version__}",
            'version': __version__,
            'isLatest': True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data['data']['taxonomy_id']

    status, data = api(
        'POST',
        'classification',
        data={
            'obj_id': obj_id1,
            'classification': 'Algol',
            'taxonomy_id': taxonomy_id,
            'probability': 1.0,
            'group_ids': [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    # Filter for candidates with classification 'Algol' - should only get obj_id1 back
    status, data = api(
        "GET",
        "candidates",
        params={"classifications": "Algol", "groupIDs": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["candidates"]) == 1
    assert data["data"]["candidates"][0]["id"] == obj_id1


def test_candidate_list_redshift_range(
    upload_data_token, view_only_token, public_filter, public_group
):
    # Post candidates with different redshifts
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 0,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 1,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200

    # Filter for candidates redshift between 0 and 0.5 - should only get obj_id1 back
    status, data = api(
        "GET",
        "candidates",
        params={
            "minRedshift": "0",
            "maxRedshift": "0.5",
            "groupIDs": f"{public_group.id}",
        },
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["candidates"]) == 1
    assert data["data"]["candidates"][0]["id"] == obj_id1


def test_exclude_by_outdated_annotations(
    annotation_token, view_only_token, public_group, public_candidate, public_candidate2
):
    status, data = api(
        "GET",
        "candidates",
        params={"groupIDs": f"{public_group.id}"},
        token=view_only_token,
    )

    assert status == 200
    num_candidates = len(data["data"]["candidates"])

    origin = str(uuid.uuid4())
    t0 = datetime.datetime.now(datetime.timezone.utc)  # recall when it was created

    # add an annotation from this origin
    status, data = api(
        "POST",
        "annotation",
        data={"obj_id": public_candidate.id, "origin": origin, "data": {'value1': 1}},
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        "candidates",
        params={"groupIDs": f"{public_group.id}", "annotationExcludeOrigin": origin},
        token=view_only_token,
    )

    assert status == 200
    assert (
        num_candidates == len(data["data"]["candidates"]) + 1
    )  # should have one less candidate

    status, data = api(
        "GET",
        "candidates",
        params={
            "groupIDs": f"{public_group.id}",
            "annotationExcludeOrigin": origin,
            "annotationExcludeOutdatedDate": str(t0 + datetime.timedelta(seconds=3)),
        },
        token=view_only_token,
    )

    assert status == 200
    assert num_candidates == len(
        data["data"]["candidates"]
    )  # should now have all the original candidates


def test_candidate_list_saved_to_all_selected_groups(
    upload_data_token_two_groups,
    view_only_token_two_groups,
    public_filter,
    public_group,
    public_group2,
):
    # Post three candidates for the same filter
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    obj_id3 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id3,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200

    # Save the two candidates as sources
    # obj_id1 is saved to both public groups
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id1, "group_ids": [public_group.id, public_group2.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1
    # obj_id2 is saved to only public_group
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id2, "group_ids": [public_group.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    # Now get candidates saved to both public_group and public_group2
    # Should not get obj_id3 back since it was not saved
    status, data = api(
        "GET",
        "candidates",
        params={
            "groupIDs": f"{public_group.id},{public_group2.id}",
            "savedStatus": "savedToAllSelected",
        },
        token=view_only_token_two_groups,
    )
    assert status == 200
    # Should only get obj_id1 back
    assert len(data["data"]["candidates"]) == 1
    assert data["data"]["candidates"][0]["id"] == obj_id1


def test_candidate_list_saved_to_any_selected_groups(
    upload_data_token_two_groups,
    view_only_token_two_groups,
    public_filter,
    public_group,
    public_group2,
):
    # Post three candidates for the same filter
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    obj_id3 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id3,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200

    # Save the two candidates as sources
    # obj_id1 is saved to only public_group2
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id1, "group_ids": [public_group2.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1
    # obj_id2 is saved to only public_group
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id2, "group_ids": [public_group.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    # Now get candidates saved to any of public_group and public_group2
    # Should not get obj_id3 back since it was not saved
    status, data = api(
        "GET",
        "candidates",
        params={
            "groupIDs": f"{public_group.id},{public_group2.id}",
            "savedStatus": "savedToAnySelected",
        },
        token=view_only_token_two_groups,
    )
    assert status == 200
    # Should get obj_id1 and obj_id2 back
    assert len(data["data"]["candidates"]) == 2
    assert (
        len(
            set([obj_id1, obj_id2]).difference(
                map(lambda x: x["id"], data["data"]["candidates"])
            )
        )
        == 0
    )


def test_candidate_list_saved_to_any_accessible_groups(
    upload_data_token_two_groups,
    view_only_token_two_groups,
    public_filter,
    public_group,
    public_group2,
):
    # Post two candidates for filter belonging to public_group
    obj_id = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200

    # obj_id is saved to only public_group2
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id, "group_ids": [public_group2.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    # Select for candidates passing public_filter, which belongs to public_group
    # Since we set "savedToAnyAccessible", should still get back obj_id even if
    # is saved to only public_group2
    # Should not get obj_id2 back since it was not saved
    status, data = api(
        "GET",
        "candidates",
        params={
            "groupIDs": f"{public_group.id}",
            "savedStatus": "savedToAnyAccessible",
        },
        token=view_only_token_two_groups,
    )
    assert status == 200
    assert len(data["data"]["candidates"]) == 1
    assert data["data"]["candidates"][0]["id"] == obj_id


def test_candidate_list_not_saved_to_any_accessible_groups(
    upload_data_token_two_groups,
    view_only_token,
    public_filter,
    public_group,
    public_group2,
):
    # Post three candidates for the same filter
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    obj_id3 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id3,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200

    # Obj_id1 is saved to public_group2
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id1, "group_ids": [public_group2.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1

    # Obj_id3 is saved to public_group
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id3, "group_ids": [public_group.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id3

    # Select for candidates passing public_filter, which belongs to public_group
    # Since we set "notSavedToAnyAccessible", should get back obj_id even though
    # it is saved, since view_only_user doesn"t have public_group2 access
    # Should also get back obj_id2 since it is not saved at all
    # Should not get back obj_id3 since it is saved to public_group
    status, data = api(
        "GET",
        "candidates",
        params={
            "groupIDs": f"{public_group.id}",
            "savedStatus": "notSavedToAnyAccessible",
        },
        token=view_only_token,
    )
    assert status == 200
    # Should get obj_id1 and obj_id2 back
    assert len(data["data"]["candidates"]) == 2
    assert (
        len(
            set([obj_id1, obj_id2]).difference(
                map(lambda x: x["id"], data["data"]["candidates"])
            )
        )
        == 0
    )


def test_candidate_list_not_saved_to_any_selected_groups(
    upload_data_token_two_groups,
    view_only_token_two_groups,
    public_filter,
    public_group,
    public_group2,
):
    # Post three candidates for the same filter
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    obj_id3 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id3,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200

    # Obj_id1 is saved to public_group2
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id1, "group_ids": [public_group2.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1

    # Obj_id3 is saved to public_group
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id3, "group_ids": [public_group.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id3

    # Select for candidates using public_group and public_group2
    # Should not get back obj_id1 since it is saved to public_group2
    # Should get back obj_id2 since it is not saved at all
    # Should not get back obj_id3 since it is saved to public_group
    status, data = api(
        "GET",
        "candidates",
        params={
            "groupIDs": f"{public_group.id},{public_group2.id}",
            "savedStatus": "notSavedToAnySelected",
        },
        token=view_only_token_two_groups,
    )
    assert status == 200
    # Should get obj_id1 back
    assert len(data["data"]["candidates"]) == 1
    assert data["data"]["candidates"][0]["id"] == obj_id2


def test_candidate_list_not_saved_to_all_selected_groups(
    upload_data_token_two_groups,
    view_only_token_two_groups,
    public_filter,
    public_group,
    public_group2,
):
    # Post three candidates for the same filter
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    obj_id3 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id3,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200

    # Obj_id1 is saved to both groups
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id1, "group_ids": [public_group.id, public_group2.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1

    # Obj_id3 is saved to public_group
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id3, "group_ids": [public_group.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id3

    # Select for candidates using public_group and public_group2
    # Should not get back obj_id since it is saved to both selected groups
    # Should get back obj_id2 since it is not saved at all
    # Should get back obj_id3 since it is saved to only public_group
    status, data = api(
        "GET",
        "candidates",
        params={
            "groupIDs": f"{public_group.id},{public_group2.id}",
            "savedStatus": "notSavedToAllSelected",
        },
        token=view_only_token_two_groups,
    )
    assert status == 200
    # Should get obj_id2 and obj_id3 back
    assert len(data["data"]["candidates"]) == 2
    assert (
        len(
            set([obj_id2, obj_id3]).difference(
                map(lambda x: x["id"], data["data"]["candidates"])
            )
        )
        == 0
    )


def test_correct_spectra_and_photometry_returned_by_candidate(
    public_candidate,
    public_candidate2,  # adds phot and spec that should not be returned
    view_only_token_two_groups,
):

    status, data = api(
        'GET',
        f"candidates/{public_candidate.id}?includePhotometry=t&includeSpectra=t",
        token=view_only_token_two_groups,
    )

    assert status == 200
    assert data['status'] == 'success'

    assert len(public_candidate.photometry) == len(data['data']['photometry'])
    assert len(public_candidate.spectra) == len(data['data']['spectra'])

    phot_ids_db = sorted([p.id for p in public_candidate.photometry])
    phot_ids_api = sorted([p['id'] for p in data['data']['photometry']])
    assert phot_ids_db == phot_ids_api

    spec_ids_db = sorted([p.id for p in public_candidate.spectra])
    spec_ids_api = sorted([p['id'] for p in data['data']['spectra']])
    assert spec_ids_db == spec_ids_api


def test_candidates_hidden_photometry_not_leaked(
    public_candidate,
    ztf_camera,
    public_group,
    public_group2,
    view_only_token,
    upload_data_token_two_groups,
):
    obj_id = str(public_candidate.id)
    # Post photometry to the object belonging to a different group
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id,
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group2.id],
            'altdata': {'some_key': 'some_value'},
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data['status'] == 'success'
    photometry_id = data['data']['ids'][0]

    # Check the photometry sent back with the candidate
    status, data = api(
        "GET",
        "candidates",
        params={"groupIDs": f"{public_group.id}", "includePhotometry": "true"},
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["candidates"]) == 1
    assert data["data"]["candidates"][0]["id"] == obj_id
    assert len(public_candidate.photometry) - 1 == len(
        data["data"]["candidates"][0]["photometry"]
    )
    assert photometry_id not in map(
        lambda x: x["id"], data["data"]["candidates"][0]["photometry"]
    )

    # Check for single GET call as well
    status, data = api(
        "GET",
        f"candidates/{obj_id}",
        params={"includePhotometry": "true"},
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id
    assert len(public_candidate.photometry) - 1 == len(data["data"]["photometry"])
    assert photometry_id not in map(lambda x: x["id"], data["data"]["photometry"])


def test_candidate_list_pagination(
    view_only_token,
    upload_data_token,
    public_group,
    public_filter,
):
    # Upload two candidates with know passed_at order
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow() + datetime.timedelta(days=1)),
        },
        token=upload_data_token,
    )
    assert status == 200

    # Default order is descending passed_at
    status, data = api(
        "GET",
        "candidates",
        params={"numPerPage": 1, "pageNumber": 2, "groupIDs": f"{public_group.id}"},
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["candidates"][0]["id"] == obj_id1
    assert "queryID" in data["data"]
    query_id = data["data"]["queryID"]

    status, data = api(
        "GET",
        "candidates",
        params={"pageNumber": 1, "queryID": query_id},
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["queryID"] == query_id

    # Wait until cache is expired
    time.sleep(3)

    # Submit new request, which will create new (unrelated) cache, triggering
    # cleanup of expired cache files
    status, data = api(
        "GET",
        "candidates",
        token=view_only_token,
    )
    assert status == 200

    # Cache should now be removed, so we expect a new query ID
    status, data = api(
        "GET",
        "candidates",
        params={"pageNumber": 1, "queryID": query_id},
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["queryID"] != query_id

    # Invalid page
    status, data = api(
        "GET",
        "candidates",
        params={"numPerPage": 1, "pageNumber": 4},
        token=view_only_token,
    )
    assert status == 400
    assert "Page number out of range" in data["message"]
