import datetime
import time
import uuid

import numpy.testing as npt
import pytest
from skyportal_py import SkyPortalError
from skyportal_py.candidates import CandidatePost
from skyportal_py.classifications import ClassificationPost
from skyportal_py.photometry import PhotometryPost
from skyportal_py.sources import SourcePost
from skyportal_py.taxonomies import TaxonomyPost
from tdtax import __version__, taxonomy

from skyportal.tests import api, client

from ....utils.naive_datetime import utcnow_naive


def test_candidate_list(view_only_token, public_candidate):
    client(view_only_token).fetch_candidates()


def test_candidate_existence(view_only_token, public_candidate):
    sp = client(view_only_token)
    assert sp.candidate_exists(public_candidate.id)

    assert not sp.candidate_exists(public_candidate.id[:-1])


def test_token_user_retrieving_candidate(view_only_token, public_candidate):
    # raw api: raw-JSON shape assertion the typed model would mask
    status, data = api(
        "GET", f"candidates/{public_candidate.id}", token=view_only_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(k in data["data"] for k in ["ra", "dec", "redshift", "dm"])
    assert "photometry" not in data["data"]


def test_token_user_retrieving_candidate_with_phot(view_only_token, public_candidate):
    candidate = client(view_only_token).fetch_candidate(
        public_candidate.id, include_photometry=True
    )
    # ra/dec/redshift/dm presence is guaranteed by the typed model
    assert candidate.photometry is not None


def test_token_user_retrieving_candidate_with_spec(view_only_token, public_candidate):
    candidate = client(view_only_token).fetch_candidate(
        public_candidate.id, include_spectra=True
    )
    # ra/dec/redshift/dm presence is guaranteed by the typed model
    assert candidate.spectra is not None


def test_token_user_post_delete_new_candidate(
    upload_data_token,
    view_only_token,
    public_filter,
):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_candidate(
        CandidatePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    candidate = client(view_only_token).fetch_candidate(obj_id)
    assert candidate.id == obj_id
    npt.assert_almost_equal(candidate.ra, 234.22)
    redshift_history = candidate.redshift_history
    assert redshift_history is not None
    assert redshift_history[-1]["value"] == 3

    client(upload_data_token).delete_candidate(obj_id, public_filter.id)


def test_token_user_post_candidate_numeric_id(
    upload_data_token,
    view_only_token,
    public_filter,
):
    # Survey ids (e.g. LSST diaObject) arrive as JSON numbers, but Obj.id is a
    # string column: without coercion Postgres rejects the varchar = bigint
    # comparison and the post 500s.
    obj_id = 170591539488620622
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "filter_ids": [public_filter.id],
            "passed_at": str(utcnow_naive()),
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api("GET", f"candidates/{obj_id}", token=view_only_token)
    assert status == 200
    assert data["data"]["id"] == str(obj_id)


def test_candidate_autosave_group_ids(
    upload_data_token_two_groups, public_filter, public_group, public_group2
):
    """autosaveGroupIds is a comma-separated list; it used to be handed to
    post_source_async as a raw string, whose per-element int() then ran on
    single characters."""
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "filter_ids": [public_filter.id],
            "passed_at": str(utcnow_naive()),
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200

    status, data = api(
        "GET",
        "candidates",
        params={
            "groupIDs": f"{public_group.id}",
            "autosave": "true",
            "autosaveGroupIds": f"{public_group.id},{public_group2.id}",
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200

    status, data = api("GET", f"sources/{obj_id}", token=upload_data_token_two_groups)
    assert status == 200
    saved_group_ids = {g["id"] for g in data["data"]["groups"]}
    assert {public_group.id, public_group2.id}.issubset(saved_group_ids)


def test_candidate_name_only_search(
    upload_data_token,
    view_only_token,
    public_filter,
):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_candidate(
        CandidatePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    # nameOnly autocomplete (toolbar quick-search): a prefix of the obj_id
    # returns the candidate's obj_id.
    page = client(view_only_token).fetch_candidates(
        obj_id=obj_id[:8], name_only=True, num_per_page=25
    )
    assert obj_id in [c.id for c in page.candidates]

    # a non-matching prefix does not return it
    page = client(view_only_token).fetch_candidates(
        obj_id="zzz-no-such-candidate", name_only=True
    )
    assert obj_id not in [c.id for c in page.candidates]


def test_cannot_add_candidate_without_filter_id(upload_data_token):
    obj_id = str(uuid.uuid4())
    # raw api: intentionally malformed payload the typed client can't produce
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
            "passed_at": str(utcnow_naive()),
        },
        token=upload_data_token,
    )
    assert status == 400


def test_cannot_add_candidate_without_passed_at(upload_data_token, public_filter):
    obj_id = str(uuid.uuid4())
    # raw api: intentionally malformed payload the typed client can't produce
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
    sp = client(upload_data_token)
    sp.post_candidate(
        CandidatePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    candidate = client(view_only_token).fetch_candidate(obj_id)
    assert candidate.id == obj_id
    npt.assert_almost_equal(candidate.ra, 234.22)

    sp.post_candidate(
        CandidatePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )


def test_token_user_repost_same_obj_filter_passed_at_is_idempotent(
    upload_data_token, view_only_token, public_filter
):
    obj_id = str(uuid.uuid4())
    passed_at = str(utcnow_naive())
    sp = client(upload_data_token)
    first_ids = sp.post_candidate(
        CandidatePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=passed_at,
        )
    ).ids

    candidate = client(view_only_token).fetch_candidate(obj_id)
    assert candidate.id == obj_id
    npt.assert_almost_equal(candidate.ra, 234.22)

    # Re-posting the same obj/filter/passed_at reuses the existing row instead of
    # 400-ing on the unique index; it returns the same candidate id.
    assert (
        sp.post_candidate(
            CandidatePost(
                id=obj_id,
                ra=234.22,
                dec=-22.33,
                redshift=3,
                transient=False,
                ra_dis=2.3,
                filter_ids=[public_filter.id],
                passed_at=passed_at,
            )
        ).ids
        == first_ids
    )


def test_repost_candidate_reuses_duplicate_and_adds_new_filter(
    upload_data_token_two_groups, public_filter, public_filter2
):
    obj_id = str(uuid.uuid4())
    passed_at = str(utcnow_naive())
    sp = client(upload_data_token_two_groups)
    first_ids = sp.post_candidate(
        CandidatePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            filter_ids=[public_filter.id],
            passed_at=passed_at,
        )
    ).ids
    assert len(first_ids) == 1

    # public_filter is a duplicate (reused), public_filter2 is genuinely new: a
    # duplicate on one filter must not drop the new candidate for the other.
    ids = sp.post_candidate(
        CandidatePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            filter_ids=[public_filter.id, public_filter2.id],
            passed_at=passed_at,
        )
    ).ids
    assert len(ids) == 2
    assert first_ids[0] in ids


def test_candidate_list_sorting_basic(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    sp = client(annotation_token)
    sp.post_annotation(public_candidate.id, origin, {"numeric_field": 1})

    sp.post_annotation(public_candidate2.id, origin, {"numeric_field": 2})

    # Sort by the numeric field so that public_candidate is returned first,
    # instead of by last_detected_at (which would put public_candidate2 first)
    page = client(view_only_token).fetch_candidates(
        sort_by_annotation_origin=f"{origin}",
        sort_by_annotation_key="numeric_field",
    )
    assert page.candidates[0].id == public_candidate.id
    assert page.candidates[1].id == public_candidate2.id


def test_candidate_list_sorting_different_origins(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    origin2 = str(uuid.uuid4())
    sp = client(annotation_token)
    sp.post_annotation(public_candidate.id, origin, {"numeric_field": 1})

    sp.post_annotation(public_candidate2.id, origin2, {"numeric_field": 2})

    # If just sorting on numeric_field, public_candidate should be returned first
    # but since we specify origin2 (which is not the origin for the
    # public_candidate annotation) public_candidate2 is returned first
    page = client(view_only_token).fetch_candidates(
        sort_by_annotation_origin=f"{origin2}",
        sort_by_annotation_key="numeric_field",
    )
    assert page.candidates[0].id == public_candidate2.id
    assert page.candidates[1].id == public_candidate.id


def test_candidate_list_sorting_hidden_group(
    annotation_token_two_groups,
    view_only_token,
    public_candidate_two_groups,
    public_candidate2,
    public_group2,
):
    sp = client(annotation_token_two_groups)
    # Post an annotation that belongs only to public_group2 (not allowed for view_only_token)
    sp.post_annotation(
        public_candidate_two_groups.id,
        f"{public_group2.id}",
        {"numeric_field": 1},
        group_ids=[public_group2.id],
    )

    # This one belongs to both public groups and is thus visible
    sp.post_annotation(
        public_candidate2.id, f"{public_group2.id}", {"numeric_field": 2}
    )

    # Sort by the numeric field ascending, but since view_only_token does not
    # have access to public_group2, the first annotation above should not be
    # seen in the response
    page = client(view_only_token).fetch_candidates(
        sort_by_annotation_origin=f"{public_group2.id}",
        sort_by_annotation_key="numeric_field",
    )
    assert page.candidates[0].id == public_candidate_two_groups.id
    assert page.candidates[0].annotations == []
    assert page.candidates[1].id == public_candidate2.id


def test_candidate_list_sorting_null_value(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    sp = client(annotation_token)
    sp.post_annotation(public_candidate.id, origin, {"numeric_field": 1})

    sp.post_annotation(public_candidate2.id, origin, {"some_other_field": 2})

    # The second candidate does not have "numeric_field" in the annotations, and
    # should thus show up after the first candidate, even though it was posted
    # latest
    page = client(view_only_token).fetch_candidates(
        sort_by_annotation_origin=f"{origin}",
        sort_by_annotation_key="numeric_field",
    )

    assert page.candidates[0].id == public_candidate.id
    assert page.candidates[1].id == public_candidate2.id


def test_candidate_list_filtering_numeric(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    sp = client(annotation_token)
    sp.post_annotation(public_candidate.id, origin, {"numeric_field": 1})

    sp.post_annotation(public_candidate2.id, origin, {"numeric_field": 2})

    # Filter by the numeric field with max value 1.5 so that only public_candidate
    # is returned
    page = client(view_only_token).fetch_candidates(
        annotation_filter_list=f'{{"origin":"{origin}","key":"numeric_field","min":0,"max":1.5}}',
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == public_candidate.id


def test_candidate_list_filtering_boolean(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    sp = client(annotation_token)
    sp.post_annotation(public_candidate.id, origin, {"bool_field": True})

    sp.post_annotation(public_candidate2.id, origin, {"bool_field": False})

    # Filter by the numeric field with value == true so that only public_candidate
    # is returned
    page = client(view_only_token).fetch_candidates(
        annotation_filter_list=f'{{"origin": "{origin}", "key": "bool_field", "value": "true"}}',
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == public_candidate.id


def test_candidate_list_filtering_string(
    annotation_token, view_only_token, public_candidate, public_candidate2
):
    origin = str(uuid.uuid4())
    sp = client(annotation_token)
    sp.post_annotation(public_candidate.id, origin, {"string_field": "a"})

    sp.post_annotation(public_candidate2.id, origin, {"string_field": "b"})

    # Filter by the numeric field with value == "a" so that only public_candidate
    # is returned
    page = client(view_only_token).fetch_candidates(
        annotation_filter_list=f'{{"origin": "{origin}", "key": "string_field", "value": "a"}}',
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == public_candidate.id


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
    sp = client(upload_data_token)
    sp.post_candidate(
        CandidatePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    sp.post_source(SourcePost(id=obj_id1))
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name="test taxonomy" + str(uuid.uuid4()),
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    client(classification_token).post_classification(
        ClassificationPost(
            obj_id=obj_id1,
            classification="Algol",
            taxonomy_id=taxonomy_id,
            probability=1.0,
            group_ids=[public_group.id],
        )
    )

    # Filter for candidates with classification 'Algol' - should only get obj_id1 back
    page = client(view_only_token).fetch_candidates(
        classifications=["Algol"], group_ids=[public_group.id]
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == obj_id1


def test_candidate_list_redshift_range(
    upload_data_token, view_only_token, public_filter, public_group
):
    # Post candidates with different redshifts
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    sp = client(upload_data_token)
    sp.post_candidate(
        CandidatePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=0,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=1,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    # Filter for candidates redshift between 0 and 0.5 - should only get obj_id1 back
    page = client(view_only_token).fetch_candidates(
        min_redshift=0,
        max_redshift=0.5,
        group_ids=[public_group.id],
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == obj_id1


def test_exclude_by_outdated_annotations(
    annotation_token, view_only_token, public_group, public_candidate, public_candidate2
):
    page = client(view_only_token).fetch_candidates(group_ids=[public_group.id])

    num_candidates = len(page.candidates)

    origin = str(uuid.uuid4())
    t0 = utcnow_naive()  # recall when it was created
    time_offset = (utcnow_naive() - datetime.datetime.now()) / datetime.timedelta(
        hours=1
    )
    t0 += datetime.timedelta(
        hours=time_offset
    )  # adjust for time zone of PC running the tests
    t0 += datetime.timedelta(seconds=60)  # give some extra time

    # add an annotation from this origin
    client(annotation_token).post_annotation(public_candidate.id, origin, {"value1": 1})


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
    sp = client(upload_data_token_two_groups)
    sp.post_candidate(
        CandidatePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id3,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    # Save the two candidates as sources
    # obj_id1 is saved to both public groups
    saved = sp.post_source(
        SourcePost(id=obj_id1, group_ids=[public_group.id, public_group2.id])
    )
    assert saved.id == obj_id1
    # obj_id2 is saved to only public_group
    saved = sp.post_source(SourcePost(id=obj_id2, group_ids=[public_group.id]))
    assert saved.id == obj_id2

    # Now get candidates saved to both public_group and public_group2
    # Should not get obj_id3 back since it was not saved
    page = client(view_only_token_two_groups).fetch_candidates(
        group_ids=[public_group.id, public_group2.id],
        saved_status="savedToAllSelected",
    )
    # Should only get obj_id1 back
    assert len(page.candidates) == 1
    assert page.candidates[0].id == obj_id1


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
    sp = client(upload_data_token_two_groups)
    sp.post_candidate(
        CandidatePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id3,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    # Save the two candidates as sources
    # obj_id1 is saved to only public_group2
    saved = sp.post_source(SourcePost(id=obj_id1, group_ids=[public_group2.id]))
    assert saved.id == obj_id1
    # obj_id2 is saved to only public_group
    saved = sp.post_source(SourcePost(id=obj_id2, group_ids=[public_group.id]))
    assert saved.id == obj_id2

    # Now get candidates saved to any of public_group and public_group2
    # Should not get obj_id3 back since it was not saved
    page = client(view_only_token_two_groups).fetch_candidates(
        group_ids=[public_group.id, public_group2.id],
        saved_status="savedToAnySelected",
    )
    # Should get obj_id1 and obj_id2 back
    assert len(page.candidates) == 2
    assert len({obj_id1, obj_id2}.difference(x.id for x in page.candidates)) == 0


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
    sp = client(upload_data_token_two_groups)
    sp.post_candidate(
        CandidatePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    # obj_id is saved to only public_group2
    saved = sp.post_source(SourcePost(id=obj_id, group_ids=[public_group2.id]))
    assert saved.id == obj_id

    # Select for candidates passing public_filter, which belongs to public_group
    # Since we set "savedToAnyAccessible", should still get back obj_id even if
    # is saved to only public_group2
    # Should not get obj_id2 back since it was not saved
    page = client(view_only_token_two_groups).fetch_candidates(
        group_ids=[public_group.id],
        saved_status="savedToAnyAccessible",
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == obj_id


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
    sp = client(upload_data_token_two_groups)
    sp.post_candidate(
        CandidatePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id3,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    # Obj_id1 is saved to public_group2
    saved = sp.post_source(SourcePost(id=obj_id1, group_ids=[public_group2.id]))
    assert saved.id == obj_id1

    # Obj_id3 is saved to public_group
    saved = sp.post_source(SourcePost(id=obj_id3, group_ids=[public_group.id]))
    assert saved.id == obj_id3

    # Select for candidates passing public_filter, which belongs to public_group
    # Since we set "notSavedToAnyAccessible", should get back obj_id even though
    # it is saved, since view_only_user doesn"t have public_group2 access
    # Should also get back obj_id2 since it is not saved at all
    # Should not get back obj_id3 since it is saved to public_group
    page = client(view_only_token).fetch_candidates(
        group_ids=[public_group.id],
        saved_status="notSavedToAnyAccessible",
    )
    # Should get obj_id1 and obj_id2 back
    assert len(page.candidates) == 2
    assert len({obj_id1, obj_id2}.difference(x.id for x in page.candidates)) == 0


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
    sp = client(upload_data_token_two_groups)
    sp.post_candidate(
        CandidatePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id3,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    # Obj_id1 is saved to public_group2
    saved = sp.post_source(SourcePost(id=obj_id1, group_ids=[public_group2.id]))
    assert saved.id == obj_id1

    # Obj_id3 is saved to public_group
    saved = sp.post_source(SourcePost(id=obj_id3, group_ids=[public_group.id]))
    assert saved.id == obj_id3

    # Select for candidates using public_group and public_group2
    # Should not get back obj_id1 since it is saved to public_group2
    # Should get back obj_id2 since it is not saved at all
    # Should not get back obj_id3 since it is saved to public_group
    page = client(view_only_token_two_groups).fetch_candidates(
        group_ids=[public_group.id, public_group2.id],
        saved_status="notSavedToAnySelected",
    )
    # Should get obj_id1 back
    assert len(page.candidates) == 1
    assert page.candidates[0].id == obj_id2


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
    sp = client(upload_data_token_two_groups)
    sp.post_candidate(
        CandidatePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id3,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    # Obj_id1 is saved to both groups
    saved = sp.post_source(
        SourcePost(id=obj_id1, group_ids=[public_group.id, public_group2.id])
    )
    assert saved.id == obj_id1

    # Obj_id3 is saved to public_group
    saved = sp.post_source(SourcePost(id=obj_id3, group_ids=[public_group.id]))
    assert saved.id == obj_id3

    # Select for candidates using public_group and public_group2
    # Should not get back obj_id since it is saved to both selected groups
    # Should get back obj_id2 since it is not saved at all
    # Should get back obj_id3 since it is saved to only public_group
    page = client(view_only_token_two_groups).fetch_candidates(
        group_ids=[public_group.id, public_group2.id],
        saved_status="notSavedToAllSelected",
    )
    # Should get obj_id2 and obj_id3 back
    assert len(page.candidates) == 2
    assert len({obj_id2, obj_id3}.difference(x.id for x in page.candidates)) == 0


def test_correct_spectra_and_photometry_returned_by_candidate(
    public_candidate,
    public_candidate2,  # adds phot and spec that should not be returned
    view_only_token_two_groups,
):
    candidate = client(view_only_token_two_groups).fetch_candidate(
        public_candidate.id, include_photometry=True, include_spectra=True
    )

    assert len(public_candidate.photometry) == len(candidate.photometry)
    assert len(public_candidate.spectra) == len(candidate.spectra)

    phot_ids_db = sorted(p.id for p in public_candidate.photometry)
    phot_ids_api = sorted(p["id"] for p in candidate.photometry)
    assert phot_ids_db == phot_ids_api

    spec_ids_db = sorted(p.id for p in public_candidate.spectra)
    spec_ids_api = sorted(p["id"] for p in candidate.spectra)
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
    photometry_id = (
        client(upload_data_token_two_groups)
        .post_photometry(
            PhotometryPost(
                obj_id=obj_id,
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                flux=12.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids=[public_group2.id],
                altdata={"some_key": "some_value"},
            )
        )
        .ids[0]
    )

    # Check the photometry sent back with the candidate
    page = client(view_only_token).fetch_candidates(
        group_ids=[public_group.id], include_photometry=True
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == obj_id
    assert len(public_candidate.photometry) - 1 == len(page.candidates[0].photometry)
    assert photometry_id not in (x["id"] for x in page.candidates[0].photometry)

    # Check for single GET call as well
    candidate = client(view_only_token).fetch_candidate(obj_id, include_photometry=True)
    assert candidate.id == obj_id
    assert len(public_candidate.photometry) - 1 == len(candidate.photometry)
    assert photometry_id not in (x["id"] for x in candidate.photometry)


def test_candidate_list_pagination(
    view_only_token,
    upload_data_token,
    public_group,
    public_filter,
):
    # Upload two candidates with know passed_at order
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    sp = client(upload_data_token)
    sp.post_candidate(
        CandidatePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp.post_candidate(
        CandidatePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive() + datetime.timedelta(days=1)),
        )
    )

    # Default order is descending passed_at
    page = client(view_only_token).fetch_candidates(
        num_per_page=1, page_number=2, group_ids=[public_group.id]
    )
    assert page.candidates[0].id == obj_id1
    assert page.query_id is not None
    query_id = page.query_id

    page = client(view_only_token).fetch_candidates(page_number=1, query_id=query_id)
    assert page.query_id == query_id

    # Wait until cache is expired
    time.sleep(3)

    # Submit new request, which will create new (unrelated) cache, triggering
    # cleanup of expired cache files
    client(view_only_token).fetch_candidates()

    # Cache should now be removed, so we expect a new query ID
    page = client(view_only_token).fetch_candidates(page_number=1, query_id=query_id)
    assert page.query_id != query_id

    # Invalid page
    with pytest.raises(SkyPortalError, match="Page number out of range") as err:
        client(view_only_token).fetch_candidates(num_per_page=1, page_number=4)
    assert err.value.status_code == 400


def test_candidates_annotation_filtering(
    public_candidate,
    ztf_camera,
    public_group,
    view_only_token,
    upload_data_token_two_groups,
    annotation_token,
):
    obj_id = str(public_candidate.id)
    # Post photometry to the object belonging to a different group
    photometry_id = (
        client(upload_data_token_two_groups)
        .post_photometry(
            PhotometryPost(
                obj_id=obj_id,
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                flux=12.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids=[public_group.id],
                altdata={"some_key": "some_value"},
            )
        )
        .ids[0]
    )

    client(annotation_token).post_annotation(
        photometry_id,
        "kowalski",
        {"gaia_G": 15.7},
        resource_type="photometry",
        group_ids=[public_group.id],
    )

    # Check the photometry sent back with the candidate
    sp = client(view_only_token)
    page = sp.fetch_candidates(
        group_ids=[public_group.id],
        photometry_annotations_filter_origin="kowalski",
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == obj_id

    page = sp.fetch_candidates(
        group_ids=[public_group.id],
        photometry_annotations_filter="gaia_G",
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == obj_id

    page = sp.fetch_candidates(
        group_ids=[public_group.id],
        photometry_annotations_filter="gaia_G : 15.0 : ge",
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == obj_id

    page = sp.fetch_candidates(
        group_ids=[public_group.id],
        photometry_annotations_filter="gaia_G : 15.0 : le",
    )
    assert len(page.candidates) == 0

    # Date-bounded filters on the photometry annotation's created_at. These
    # exercise the AnnotationOnPhotometry.created_at (timestamp) comparison: the
    # date string must be coerced to a datetime or psycopg3 raises "operator
    # does not exist: timestamp without time zone = character varying".
    page = sp.fetch_candidates(
        group_ids=[public_group.id],
        photometry_annotations_filter_origin="kowalski",
        photometry_annotations_filter_after="2000-01-01T00:00:00",
    )
    assert len(page.candidates) == 1
    assert page.candidates[0].id == obj_id

    page = sp.fetch_candidates(
        group_ids=[public_group.id],
        photometry_annotations_filter_origin="kowalski",
        photometry_annotations_filter_before="2000-01-01T00:00:00",
    )
    assert len(page.candidates) == 0


def test_candidate_savers(
    upload_data_token,
    upload_data_token_two_groups,
    view_only_token,
    public_filter,
    public_group,
):
    # Post three candidates for the same filter
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    obj_id3 = str(uuid.uuid4())
    sp_two_groups = client(upload_data_token_two_groups)
    sp_two_groups.post_candidate(
        CandidatePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp_two_groups.post_candidate(
        CandidatePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )
    sp_two_groups.post_candidate(
        CandidatePost(
            id=obj_id3,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            filter_ids=[public_filter.id],
            passed_at=str(utcnow_naive()),
        )
    )

    # Save the three candidates as sources
    # obj_id1 is saved by the upload_data_token token
    saved = client(upload_data_token).post_source(
        SourcePost(id=obj_id1, group_ids=[public_group.id])
    )
    assert saved.id == obj_id1

    # obj_id2 is also saved by the upload_data_token token
    saved = client(upload_data_token).post_source(
        SourcePost(id=obj_id2, group_ids=[public_group.id])
    )
    assert saved.id == obj_id2

    # obj_id3 is saved by the upload_data_token_two_groups token
    saved = sp_two_groups.post_source(
        SourcePost(id=obj_id3, group_ids=[public_group.id])
    )
    assert saved.id == obj_id3

    # Check scanning statistics
    # raw api: internal dashboard-widget endpoint, outside skyportal-py's scope
    status, data = api(
        "GET",
        "internal/source_savers",
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"

    assert len(data["data"]) == 2
    assert data["data"][0]["saves"] == 2
    assert data["data"][1]["saves"] == 1


def test_candidate_filter_list(view_only_token, public_candidate):
    # raw api: raw-JSON shape assertion the typed model would mask
    status, data = api("GET", "candidates_filter", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["candidates"]) >= 1
    assert "totalMatches" in data["data"]
    assert isinstance(data["data"]["totalMatches"], int)
    assert "passing_alert_id" in data["data"]["candidates"][0]
    assert "obj_id" in data["data"]["candidates"][0]


def test_bulk_delete_old_unsaved_candidates(
    super_admin_token, upload_data_token, view_only_token, public_filter, public_group
):
    old = str(utcnow_naive() - datetime.timedelta(days=400))  # > 6 months
    recent = str(utcnow_naive())

    old_unsaved = str(uuid.uuid4())  # old + never saved -> should be deleted
    old_saved = str(uuid.uuid4())  # old but actively saved -> should be kept
    recent_unsaved = str(uuid.uuid4())  # unsaved but recent -> should be kept

    sp = client(upload_data_token)
    for obj_id, passed_at in [
        (old_unsaved, old),
        (old_saved, old),
        (recent_unsaved, recent),
    ]:
        sp.post_candidate(
            CandidatePost(
                id=obj_id,
                ra=10.0,
                dec=10.0,
                filter_ids=[public_filter.id],
                passed_at=passed_at,
            )
        )

    # save old_saved as an active source so it is protected
    sp.post_source(SourcePost(id=old_saved, group_ids=[public_group.id]))

    # non-admins cannot call the purge
    sp_view = client(view_only_token)
    with pytest.raises(SkyPortalError) as err:
        sp_view.bulk_delete_candidates()
    assert err.value.status_code == 401

    # dry run deletes nothing but reports the old, unsaved candidate
    result = client(super_admin_token).bulk_delete_candidates(
        max_age_months=6, dry_run=True
    )
    assert result.deleted == 0
    assert result.remaining >= 1
    # dry run did not actually delete
    assert sp_view.candidate_exists(old_unsaved)

    # real purge
    result = client(super_admin_token).bulk_delete_candidates(max_age_months=6)
    assert result.deleted >= 1

    # old + unsaved was deleted
    assert not sp_view.candidate_exists(old_unsaved)
    # old + saved was kept (has an active source)
    assert sp_view.candidate_exists(old_saved)
    # recent + unsaved was kept (too new)
    assert sp_view.candidate_exists(recent_unsaved)
