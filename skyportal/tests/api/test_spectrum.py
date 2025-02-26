import datetime
import os
import time
import uuid
from glob import glob

import arrow
import numpy as np
import yaml

from skyportal.enum_types import ALLOWED_SPECTRUM_TYPES, default_spectrum_type
from skyportal.tests import api


def test_spectrum_put(super_admin_user, super_admin_token, public_source, lris):
    # make groups that must be unique to this test
    status, data = api(
        "POST",
        "groups",
        data={
            "name": str(uuid.uuid4()),
            "group_admins": [super_admin_user.id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    group_id1 = data["data"]["id"]

    status, data = api(
        "POST",
        "groups",
        data={
            "name": str(uuid.uuid4()),
            "group_admins": [super_admin_user.id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    group_id2 = data["data"]["id"]

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [group_id1],
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id = data["data"]["id"]

    assert status == 200
    assert data["status"] == "success"

    # update only the label
    custom_label = str(uuid.uuid4())
    status, data = api(
        "PUT",
        f"spectrum/{spectrum_id}",
        data={
            "label": custom_label,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"spectrum/{spectrum_id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["label"] == custom_label
    group_ids = [g["id"] for g in data["data"]["groups"]]
    assert group_id1 in group_ids
    assert group_id2 not in group_ids

    # update the group IDs (should ADD group2, not remove group1)
    status, data = api(
        "PUT",
        f"spectrum/{spectrum_id}",
        data={"group_ids": [group_id2]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"spectrum/{spectrum_id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["label"] == custom_label
    group_ids = [g["id"] for g in data["data"]["groups"]]
    assert group_id1 in group_ids  # PUT is only allowed to remove groups
    assert group_id2 in group_ids
    num_groups = len(data["data"]["groups"])

    # adding the same group ID doesn't make redundant groups
    status, data = api(
        "PUT",
        f"spectrum/{spectrum_id}",
        data={"group_ids": [group_id1]},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"spectrum/{spectrum_id}",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert num_groups == len(data["data"]["groups"])


def test_spectrum_filtering_obj_groups(
    super_admin_user,
    super_admin_token,
    public_source,
    public_source_two_groups,
    lris,
):
    # make groups that must be unique to this test
    status, data = api(
        "POST",
        "groups",
        data={
            "name": str(uuid.uuid4()),
            "group_admins": [super_admin_user.id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    group_id1 = data["data"]["id"]

    status, data = api(
        "POST",
        "groups",
        data={
            "name": str(uuid.uuid4()),
            "group_admins": [super_admin_user.id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    group_id2 = data["data"]["id"]

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [group_id1],
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id1 = data["data"]["id"]

    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source_two_groups.id,
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [434.7, 432.1, 435.3],
            "group_ids": [group_id1, group_id2],
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id2 = data["data"]["id"]

    # filter on groups:
    status, data = api(
        "GET",
        "spectra",
        params={"groupIDs": group_id1},  # should get both spectra
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 2
    assert data["data"][0]["id"] == spectrum_id1
    assert data["data"][1]["id"] == spectrum_id2
    assert data["data"][0]["fluxes"][0] == 234.3
    assert data["data"][1]["fluxes"][0] == 434.7

    status, data = api(
        "GET",
        "spectra",
        params={"groupIDs": f"{group_id1}, {group_id2}"},  # should get both spectra
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 2
    assert data["data"][0]["id"] == spectrum_id1
    assert data["data"][1]["id"] == spectrum_id2

    status, data = api(
        "GET",
        "spectra",
        params={"groupIDs": group_id2},  # should get only second spectrum
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id2

    # test objID
    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id1,
            "objID": public_source.id,  # should get only first spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id1

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id1,
            # partial match to second spectrum
            "objID": public_source_two_groups.id[5:15],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id2

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id1,
            "objID": "ZTF2022abcdef",  # should not match anything
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 0


def test_spectrum_filtering_time_ranges(
    super_admin_user,
    super_admin_token,
    public_source,
    lris,
):
    # make a group that is unique to this test
    status, data = api(
        "POST",
        "groups",
        data={
            "name": str(uuid.uuid4()),
            "group_admins": [super_admin_user.id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    group_id = data["data"]["id"]

    # post two spectra at different times
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [group_id],
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id1 = data["data"]["id"]

    time_after_posting_first_spec = str(datetime.datetime.utcnow())

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": time_after_posting_first_spec,
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [434.7, 432.1, 435.3],
            "group_ids": [group_id],
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id2 = data["data"]["id"]

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "observedBefore": "2021-01-10T00:00:00",  # one year after 1st spectrum
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id1
    assert data["data"][0]["fluxes"][0] == 234.3
    assert data["data"][0]["obj_id"] == public_source.id

    # test open ended range that includes second spectrum
    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "observedAfter": time_after_posting_first_spec,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id2
    assert data["data"][0]["fluxes"][0] == 434.7
    assert data["data"][0]["obj_id"] == public_source.id

    # test open ended range that includes both spectra
    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "observedAfter": "2020-01-01T00:00:00",
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 2

    # test various date formats
    # can't parse this: 'T00:00:00&plus;00:00'
    dates = ["", "T00:00:00+00:00", "T00:00:00Z"]
    for d in dates:
        status, data = api(
            "GET",
            "spectra",
            params={
                "groupIDs": group_id,
                "observedAfter": f"2020-01-15{d}",  # should get only second spectrum
            },
            token=super_admin_token,
        )

        assert status == 200
        assert data["status"] == "success"
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == spectrum_id2


def test_spectrum_filtering_id_lists(
    super_admin_user,
    super_admin_token,
    comment_token,
    public_source,
    lris,
    sedm,
    public_source_followup_request,
    public_source_group2_followup_request,
    public_assignment,
):
    # make a group that is unique to this test
    status, data = api(
        "POST",
        "groups",
        data={
            "name": str(uuid.uuid4()),
            "group_admins": [super_admin_user.id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    group_id = data["data"]["id"]

    # post two spectra with very different properties
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [group_id],
            "followup_request_id": public_source_followup_request.id,
            "assignment_id": public_assignment.id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id1 = data["data"]["id"]

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": str(datetime.datetime.utcnow()),
            "instrument_id": sedm.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [434.7, 432.1, 435.3],
            "group_ids": [group_id],
            "followup_request_id": public_source_group2_followup_request.id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id2 = data["data"]["id"]

    # test instrument IDs
    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "instrumentIDs": lris.id,  # should get only first spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id1

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "instrumentIDs": sedm.id,  # should get only second spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id2

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "instrumentIDs": f"{lris.id}, {sedm.id}",  # should get both
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 2

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "instrumentIDs": f"{lris.id}, {sedm.id}, {lris.id * sedm.id}",  # should fail
        },
        token=super_admin_token,
    )

    assert status == 400
    assert data["status"] == "error"
    assert "Not all Instrument IDs" in data["message"]

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "instrumentIDs": "free text",  # should fail
        },
        token=super_admin_token,
    )

    assert status == 400
    assert data["status"] == "error"
    assert "Could not parse all elements to integers" in data["message"]

    # test followup request IDs
    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "followupRequestIDs": public_source_followup_request.id,  # should get only first spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id1

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "followupRequestIDs": public_source_group2_followup_request.id,  # should only get second spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id2

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            # should get error
            "followupRequestIDs": public_source_group2_followup_request.id * 10,
        },
        token=super_admin_token,
    )

    assert status == 400
    assert data["status"] == "error"
    assert "Not all FollowupRequest IDs" in data["message"]

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "followupRequestIDs": public_source_group2_followup_request.id,
        },
        token=comment_token,  # should fail due to permission to see followup request
    )

    assert status == 400
    assert data["status"] == "error"
    assert "Not all FollowupRequest IDs" in data["message"]

    # test assignments
    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "assignmentIDs": public_assignment.id,  # should get only first spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id1

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "assignmentIDs": public_assignment.id * 10,  # should fail
        },
        token=super_admin_token,
    )

    assert status == 400
    assert data["status"] == "error"
    assert "Not all ClassicalAssignment IDs" in data["message"]


def test_spectrum_filtering_origin_label_type(
    super_admin_user,
    super_admin_token,
    public_source,
    lris,
):
    # make a group that is unique to this test
    status, data = api(
        "POST",
        "groups",
        data={
            "name": str(uuid.uuid4()),
            "group_admins": [super_admin_user.id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    group_id = data["data"]["id"]

    # post two spectra with very different properties
    custom_label = str(uuid.uuid4())
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [group_id],
            "label": custom_label,
            "origin": "Keck telescope",
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id1 = data["data"]["id"]

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": str(datetime.datetime.utcnow()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [434.7, 432.1, 435.3],
            "group_ids": [group_id],
            "type": "host",
            "origin": "Palomar 60 inch",
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id2 = data["data"]["id"]

    # test origin
    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "origin": "Keck",  # should get only first spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id1

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "origin": ["Gemini", "VLT"],  # should get nothing
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 0

    # test label
    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "label": custom_label,  # should get only first spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id1

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "label": ["one", "two", "three"],  # should get nothing
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 0

    # test type
    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "type": "source",  # should get only first spectrum (default type)
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id1

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "type": "host",  # should get only second spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id2

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "type": "host_center",  # should get nothing
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 0

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "type": "rainbow",  # should get error, (allowed enum)
        },
        token=super_admin_token,
    )

    assert status == 400
    assert data["status"] == "error"
    assert "not in list of allowed spectrum types" in data["message"]


def test_spectrum_filtering_comments(
    super_admin_user,
    super_admin_token,
    upload_data_token,
    comment_token,
    public_source,
    lris,
):
    # make a group that is unique to this test
    status, data = api(
        "POST",
        "groups",
        data={
            "name": str(uuid.uuid4()),
            # "group_admins": [super_admin_user.id],
        },
        token=upload_data_token,
    )

    assert status == 200
    assert data["status"] == "success"
    group_id = data["data"]["id"]

    # post two spectra with very different properties
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [group_id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id1 = data["data"]["id"]

    comment_text = str(uuid.uuid4())
    status, data = api(
        "POST",
        f"spectra/{spectrum_id1}/comments",
        data={"text": comment_text, "group_ids": [group_id]},
        token=comment_token,
    )

    assert status == 200
    assert data["status"] == "success"

    time.sleep(2)
    time_after_posting_first_spec = str(datetime.datetime.utcnow())

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": time_after_posting_first_spec,
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [434.7, 432.1, 435.3],
            "group_ids": [group_id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id2 = data["data"]["id"]

    status, data = api(
        "POST",
        f"spectra/{spectrum_id2}/comments",
        data={
            "text": "looks like Ia.",
            "group_ids": [group_id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "commentsFilter": comment_text[10:20],  # should get first spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id1

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            # should get second spectrum
            "commentsFilterAuthor": super_admin_user.username[8:16],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id2

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "commentsFilterAuthor": str(uuid.uuid4()),  # should get nothing
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 0
    time_offset = (
        datetime.datetime.utcnow() - datetime.datetime.now()
    ) / datetime.timedelta(hours=1)

    comment_created_time = str(
        arrow.get(time_after_posting_first_spec)
        .shift(seconds=-1)
        .shift(hours=time_offset)
    )
    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "commentsFilterBefore": comment_created_time,  # should get first spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id1

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "commentsFilterAfter": comment_created_time,  # should get second spectrum
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == spectrum_id2


def test_minimal_spectrum(
    super_admin_token,
    public_source,
    lris,
    public_assignment,
    public_source_followup_request,
):
    # make a group that is unique to this test
    status, data = api(
        "POST",
        "groups",
        data={
            "name": str(uuid.uuid4()),
            # "group_admins": [super_admin_user.id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    group_id = data["data"]["id"]

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [group_id],
            "followup_request_id": public_source_followup_request.id,
            "assignment_id": public_assignment.id,
            "origin": str(uuid.uuid4()),
            "type": "host",
            "label": str(uuid.uuid4()),
            "altdata": {"one": 1, "two": 2},
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id = data["data"]["id"]

    # post a comment and an annotation as well
    status, data = api(
        "POST",
        f"spectra/{spectrum_id}/comments",
        data={"text": str(uuid.uuid4()), "group_ids": [group_id]},
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "POST",
        f"spectra/{spectrum_id}/annotations",
        data={
            "data": {
                "Gaia_Rp": 14.7,
                "Gaia_Bp": 15.2,
                "Gaia_G": 14.9,
                "period": 13.4,
            },
            "origin": "Kowalski",
            "group_ids": [group_id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"spectra/{spectrum_id}",
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], dict)
    assert data["data"]["id"] == spectrum_id
    single_spec = data["data"]

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "minimalPayload": False,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 1
    full_spec = data["data"][0]

    status, data = api(
        "GET",
        "spectra",
        params={
            "groupIDs": group_id,
            "minimalPayload": True,
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 1
    minimal_spec = data["data"][0]

    list_of_keys = [
        "id",
        "altdata",
        "assignment_id",
        "followup_request_id",
        "instrument_id",
        "label",
        "obj_id",
        "observed_at",
        "origin",
        "owner_id",
        "type",
        "original_file_filename",
        "created_at",
        "modified",
    ]

    # make sure the minimal list of keys exists in each output
    for k in list_of_keys:
        assert k in minimal_spec  # using multiple spectra, minimal output
        assert k in full_spec  # using multiple spectra, full output
        assert k in single_spec  # using single spectra (should be full always)
        assert minimal_spec[k] == full_spec[k]

    # check that keys of full spec, outside the minimal list, are not included in minimal
    for k in full_spec:
        assert k in list_of_keys or k not in minimal_spec

    # make sure full and single are the same
    for k in single_spec:
        assert k in full_spec
        assert single_spec[k] == full_spec[k]


def test_token_user_get_range_spectrum(
    upload_data_token, public_source, public_group, lris
):
    # post two spectra at two different dates
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [434.2, 432.1, 435.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # test range that includes first spectrum
    status, data = api(
        "GET",
        f"spectrum/range?instrument_ids={lris.id}"
        f"&min_date=2020-01-01T00:00:00&max_date=2020-01-15T00:00:00",
        token=upload_data_token,
    )
    assert status == 200
    assert len(data["data"]) == 1
    assert data["status"] == "success"
    assert data["data"][0]["fluxes"][0] == 234.2
    assert data["data"][0]["obj_id"] == public_source.id

    # test open ended range that includes second spectrum
    status, data = api(
        "GET",
        f"spectrum/range?instrument_ids={lris.id}&min_date=2020-01-15T00:00:00",
        token=upload_data_token,
    )
    assert status == 200
    assert len(data["data"]) == 1
    assert data["status"] == "success"
    assert data["data"][0]["fluxes"][0] == 434.2
    assert data["data"][0]["obj_id"] == public_source.id

    # test open ended range that includes both spectra
    status, data = api(
        "GET",
        f"spectrum/range?instrument_ids={lris.id}&min_date=2020-01-01T00:00:00",
        token=upload_data_token,
    )
    assert status == 200
    assert len(data["data"]) == 2
    assert data["status"] == "success"

    # test legal variations on input isot format
    # 2020-01-15
    status, data = api(
        "GET",
        f"spectrum/range?instrument_ids={lris.id}&min_date=2020-01-15",
        token=upload_data_token,
    )
    assert status == 200
    assert len(data["data"]) == 1
    assert data["status"] == "success"
    assert data["data"][0]["fluxes"][0] == 434.2
    assert data["data"][0]["obj_id"] == public_source.id

    # 2020-01-15T00:00:00+00:00
    status, data = api(
        "GET",
        f"spectrum/range?instrument_ids={lris.id}&min_date=2020-01-15T00:00:00&plus;00:00",
        token=upload_data_token,
    )
    assert status == 200
    assert len(data["data"]) == 1
    assert data["status"] == "success"
    assert data["data"][0]["fluxes"][0] == 434.2
    assert data["data"][0]["obj_id"] == public_source.id

    # 2020-01-15T00:00:00Z
    status, data = api(
        "GET",
        f"spectrum/range?instrument_ids={lris.id}&min_date=2020-01-15T00:00:00Z",
        token=upload_data_token,
    )
    assert status == 200
    assert len(data["data"]) == 1
    assert data["status"] == "success"
    assert data["data"][0]["fluxes"][0] == 434.2
    assert data["data"][0]["obj_id"] == public_source.id

    # test with no instrument ids
    status, data = api(
        "GET",
        "spectrum/range?min_date=2020-01-01T00:00:00&max_date=2020-02-01",
        token=upload_data_token,
    )
    assert status == 200
    assert len(data["data"]) == 1
    assert data["status"] == "success"
    assert data["data"][0]["fluxes"][0] == 234.2
    assert data["data"][0]["obj_id"] == public_source.id


def test_token_user_post_get_spectrum_data(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 234.2
    assert data["data"]["obj_id"] == public_source.id


def test_token_user_post_spectrum_no_instrument_id(
    upload_data_token, public_source, public_group
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"

    # should be a marshamallow error, not a psycopg2 error
    # (see https://github.com/skyportal/skyportal/issues/1047)
    assert "psycopg2" not in data["message"]


def test_token_user_post_spectrum_all_groups(
    upload_data_token, public_source_two_groups, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source_two_groups.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": "all",
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 234.2
    assert data["data"]["obj_id"] == public_source_two_groups.id


def test_token_user_post_spectrum_no_access(
    view_only_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=view_only_token,
    )
    assert status == 401
    assert data["status"] == "error"


def test_token_user_update_spectrum(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 234.2

    status, data = api(
        "PUT",
        f"spectrum/{spectrum_id}",
        data={
            "fluxes": [222.2, 232.1, 235.3],
            "observed_at": str(datetime.datetime.now()),
            "wavelengths": [664, 665, 666],
            "group_ids": "all",
        },
        token=upload_data_token,
    )

    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 222.2
    # test that length of groups is greater than 1 after adding all groups to the spectrum
    assert len(data["data"]["groups"]) > 1


def test_token_user_cannot_update_unowned_spectrum(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 234.2

    status, data = api(
        "PUT",
        f"spectrum/{spectrum_id}",
        data={
            "fluxes": [222.2, 232.1, 235.3],
            "observed_at": str(datetime.datetime.now()),
            "wavelengths": [664, 665, 666],
        },
        token=manage_sources_token,
    )

    assert status == 401
    assert data["status"] == "error"


def test_admin_can_update_unowned_spectrum_data(
    upload_data_token, super_admin_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 234.2

    status, data = api(
        "PUT",
        f"spectrum/{spectrum_id}",
        data={
            "fluxes": [222.2, 232.1, 235.3],
            "observed_at": str(datetime.datetime.now()),
            "wavelengths": [664, 665, 666],
            "group_ids": [2, 3],
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 222.2
    # check if length of groups is 4 after adding permission to two groups (groups with id 2 and 3) because two groups already have permission to this spectrum (groups with id 1405 and 1406)
    assert len(data["data"]["groups"]) == 4


def test_spectrum_owner_id_is_unmodifiable(
    upload_data_token,
    super_admin_user,
    super_admin_token,
    public_source,
    public_group,
    lris,
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 234.2

    status, data = api(
        "PUT",
        f"spectrum/{spectrum_id}",
        data={"owner_id": super_admin_user.id},
        token=super_admin_token,
    )

    assert status == 400
    assert data["status"] == "error"


def test_user_cannot_delete_unowned_spectrum_data(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 234.2
    assert data["data"]["obj_id"] == public_source.id

    status, data = api("DELETE", f"spectrum/{spectrum_id}", token=manage_sources_token)
    assert status == 401


def test_user_can_delete_owned_spectrum_data(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 234.2
    assert data["data"]["obj_id"] == public_source.id

    status, data = api("DELETE", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200

    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 403


def test_admin_can_delete_unowned_spectrum_data(
    upload_data_token, super_admin_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["fluxes"][0] == 234.2
    assert data["data"]["obj_id"] == public_source.id

    status, data = api("DELETE", f"spectrum/{spectrum_id}", token=super_admin_token)
    assert status == 200

    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 403


def test_jsonify_spectrum_header(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    for filename in glob(f"{os.path.dirname(__file__)}/../data/ZTF*.ascii.head"):
        with open(filename[:-5]) as f:
            status, data = api(
                "POST",
                "spectrum/parse/ascii",
                data={
                    "fluxerr_column": 3
                    if "ZTF20abpuxna_20200915_Keck1_v1.ascii" in filename
                    else 2
                    if "P60" in filename
                    else None,
                    "ascii": f.read(),
                },
                token=upload_data_token,
            )
        assert status == 200
        assert data["status"] == "success"

        answer = yaml.safe_load(open(filename))

        # check the header serialization
        for key in answer:
            # special keys
            if key not in ["COMMENT", "END", "HISTORY"]:
                if isinstance(data["data"]["altdata"][key], dict):
                    value = data["data"]["altdata"][key]["value"]
                else:
                    value = data["data"]["altdata"][key]
                if isinstance(answer[key], str | int):
                    assert str(value) == str(answer[key])
                elif isinstance(answer[key], datetime.datetime):
                    assert datetime.datetime.fromisoformat(value) == answer[key]
                elif isinstance(answer[key], datetime.date):
                    assert datetime.datetime.fromisoformat(value).date() == answer[key]
                elif answer[key] is None:
                    assert value is None
                else:
                    np.testing.assert_allclose(value, answer[key])


def test_can_post_spectrum_no_groups(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["groups"]) == 1


def test_can_post_spectrum_empty_groups_list(
    upload_data_token, public_source, public_group, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["groups"]) == 1


def test_jsonify_spectrum_data(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    for filename in glob(f"{os.path.dirname(__file__)}/../data/ZTF*.ascii"):
        with open(filename) as f:
            status, data = api(
                "POST",
                "spectrum/parse/ascii",
                data={
                    "fluxerr_column": 3
                    if "ZTF20abpuxna_20200915_Keck1_v1.ascii" in filename
                    else 2
                    if "P60" in filename
                    else None,
                    "ascii": f.read(),
                },
                token=upload_data_token,
            )
        assert status == 200
        assert data["status"] == "success"

        answer = np.genfromtxt(filename, dtype=float, encoding="ascii")

        if answer.shape[-1] == 2:
            np.testing.assert_allclose(
                np.asarray(data["data"]["wavelengths"], dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(data["data"]["fluxes"], dtype=float), answer[:, 1]
            )

        elif answer.shape[-1] == 3:
            np.testing.assert_allclose(
                np.asarray(data["data"]["wavelengths"], dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(data["data"]["fluxes"], dtype=float), answer[:, 1]
            )
            np.testing.assert_allclose(
                np.asarray(data["data"]["errors"], dtype=float), answer[:, 2]
            )

        else:
            # this is the long one from Keck
            np.testing.assert_allclose(
                np.asarray(data["data"]["wavelengths"], dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(data["data"]["fluxes"], dtype=float), answer[:, 1]
            )
            np.testing.assert_allclose(
                np.asarray(data["data"]["errors"], dtype=float), answer[:, 3]
            )


def test_upload_bad_spectrum_from_ascii_file(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    for filename in glob(f"{os.path.dirname(__file__)}/../data/ZTF*.ascii.bad"):
        with open(filename) as f:
            content = f.read()
            observed_at = str(datetime.datetime.now())

            status, data = api(
                "POST",
                "spectrum/ascii",
                data={
                    "obj_id": str(public_source.id),
                    "observed_at": observed_at,
                    "instrument_id": lris.id,
                    "group_ids": [public_group.id],
                    "fluxerr_column": 3
                    if "ZTF20abpuxna_20200915_Keck1_v1.ascii" in filename
                    else 2
                    if "P60" in filename
                    else None,
                    "ascii": content,
                    "filename": filename,
                },
                token=upload_data_token,
            )

            assert status == 400
            assert data["status"] == "error"


def test_token_user_post_to_foreign_group_and_retrieve(
    upload_data_token, public_source_two_groups, public_group2, lris
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source_two_groups.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200


def test_parse_integer_spectrum_ascii(upload_data_token):
    status, data = api(
        "POST",
        "spectrum/parse/ascii",
        data={"ascii": "4000 0.01\n4500 0.02\n5000 0.005\n5500 0.006\n6000 0.01\n"},
        token=upload_data_token,
    )

    assert status == 200
    assert data["status"] == "success"

    for wave in data["data"]["wavelengths"]:
        assert isinstance(wave, float)


def test_spectrum_external_reducer_and_observer(
    upload_data_token, public_source, public_group, lris, user
):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
            "reduced_by": [user.id],
            "external_reducer": "Test external reducer",
            "observed_by": [user.id],
            "external_observer": "Test external observer",
            "pi": [user.id],
            "external_pi": "Test external PI",
        },
        token=upload_data_token,
    )
    print(data)
    assert status == 200
    assert data["status"] == "success"

    spectrum_id = data["data"]["id"]
    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["reducers"][0]["id"] == user.id
    assert data["data"]["observers"][0]["id"] == user.id
    assert data["data"]["pis"][0]["id"] == user.id
    assert data["data"]["external_reducer"] == "Test external reducer"
    assert data["data"]["external_observer"] == "Test external observer"
    assert data["data"]["external_pi"] == "Test external PI"


def test_post_get_spectrum_type(upload_data_token, public_source, public_group, lris):
    # post this spectrum without a type (should default to "source")
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id = data["data"]["id"]

    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["type"] == default_spectrum_type

    assert default_spectrum_type in ALLOWED_SPECTRUM_TYPES

    if len(ALLOWED_SPECTRUM_TYPES) > 1:
        new_allowed_types = list(ALLOWED_SPECTRUM_TYPES)
        new_allowed_types.remove(default_spectrum_type)

        status, data = api(
            "POST",
            "spectrum",
            data={
                "obj_id": str(public_source.id),
                "observed_at": str(datetime.datetime.now()),
                "instrument_id": lris.id,
                "wavelengths": [664, 665, 666],
                "fluxes": [234.2, 232.1, 235.3],
                "group_ids": [public_group.id],
                "type": new_allowed_types[0],
            },
            token=upload_data_token,
        )
        assert status == 200
        assert data["status"] == "success"
        spectrum_id = data["data"]["id"]

        status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
        assert status == 200
        assert data["status"] == "success"
        assert data["data"]["type"] == new_allowed_types[0]


def test_post_wrong_spectrum_type(upload_data_token, public_source, public_group, lris):
    # post this spectrum with the wrong type
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
            "type": str(uuid.uuid4()),
        },
        token=upload_data_token,
    )
    assert status == 400
    assert "Must be one of: " in data["message"]
