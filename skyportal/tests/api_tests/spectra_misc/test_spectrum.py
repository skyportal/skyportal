import datetime
import os
import time
import uuid
from glob import glob

import arrow
import numpy as np
import pytest
import yaml
from skyportal_py import SkyPortalError
from skyportal_py.groups import GroupPost
from skyportal_py.spectra import (
    SpectrumAsciiParse,
    SpectrumAsciiPost,
    SpectrumPost,
    SpectrumUpdate,
)

from skyportal.enum_types import ALLOWED_SPECTRUM_TYPES, default_spectrum_type
from skyportal.tests import api, client

from ....utils.naive_datetime import utcnow_naive


def test_spectrum_put(super_admin_user, super_admin_token, public_source, lris):
    sp = client(super_admin_token)

    # make groups that must be unique to this test
    group_id1 = sp.post_group(
        GroupPost(
            name=str(uuid.uuid4()),
            group_admins=[super_admin_user.id],
        )
    ).id

    group_id2 = sp.post_group(
        GroupPost(
            name=str(uuid.uuid4()),
            group_admins=[super_admin_user.id],
        )
    ).id

    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at="2020-01-10T00:00:00",
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.3, 232.1, 235.3],
            group_ids=[group_id1],
        )
    ).id

    # update only the label
    custom_label = str(uuid.uuid4())
    sp.update_spectrum(spectrum_id, SpectrumUpdate(label=custom_label))

    spectrum = sp.fetch_spectrum(spectrum_id)
    assert spectrum.label == custom_label
    group_ids = [g.id for g in spectrum.groups]
    assert group_id1 in group_ids
    assert group_id2 not in group_ids

    # update the group IDs (should ADD group2, not remove group1)
    sp.update_spectrum(spectrum_id, SpectrumUpdate(group_ids=[group_id2]))

    spectrum = sp.fetch_spectrum(spectrum_id)
    assert spectrum.label == custom_label
    group_ids = [g.id for g in spectrum.groups]
    assert group_id1 in group_ids  # PUT is only allowed to remove groups
    assert group_id2 in group_ids
    num_groups = len(spectrum.groups)

    # adding the same group ID doesn't make redundant groups
    sp.update_spectrum(spectrum_id, SpectrumUpdate(group_ids=[group_id1]))

    assert num_groups == len(sp.fetch_spectrum(spectrum_id).groups)


def test_spectrum_filtering_obj_groups(
    super_admin_user,
    super_admin_token,
    public_source,
    public_source_two_groups,
    lris,
):
    sp = client(super_admin_token)

    # make groups that must be unique to this test
    group_id1 = sp.post_group(
        GroupPost(
            name=str(uuid.uuid4()),
            group_admins=[super_admin_user.id],
        )
    ).id

    group_id2 = sp.post_group(
        GroupPost(
            name=str(uuid.uuid4()),
            group_admins=[super_admin_user.id],
        )
    ).id

    spectrum_id1 = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at="2020-01-10T00:00:00",
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.3, 232.1, 235.3],
            group_ids=[group_id1],
        )
    ).id

    spectrum_id2 = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source_two_groups.id,
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[434.7, 432.1, 435.3],
            group_ids=[group_id1, group_id2],
        )
    ).id

    # filter on groups:
    spectra = sp.fetch_spectra_query(group_ids=[group_id1])  # should get both spectra
    assert len(spectra) == 2
    assert spectra[0].id == spectrum_id1
    assert spectra[1].id == spectrum_id2
    assert spectra[0].fluxes[0] == 234.3
    assert spectra[1].fluxes[0] == 434.7

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id1, group_id2]  # should get both spectra
    )
    assert len(spectra) == 2
    assert spectra[0].id == spectrum_id1
    assert spectra[1].id == spectrum_id2

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id2]  # should get only second spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id2

    # test objID
    spectra = sp.fetch_spectra_query(
        group_ids=[group_id1],
        obj_id=public_source.id,  # should get only first spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id1

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id1],
        # partial match to second spectrum
        obj_id=public_source_two_groups.id[5:15],
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id2

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id1],
        obj_id="ZTF2022abcdef",  # should not match anything
    )
    assert len(spectra) == 0


def test_spectrum_filtering_time_ranges(
    super_admin_user,
    super_admin_token,
    public_source,
    lris,
):
    sp = client(super_admin_token)

    # make a group that is unique to this test
    group_id = sp.post_group(
        GroupPost(
            name=str(uuid.uuid4()),
            group_admins=[super_admin_user.id],
        )
    ).id

    # post two spectra at different times
    spectrum_id1 = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at="2020-01-10T00:00:00",
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.3, 232.1, 235.3],
            group_ids=[group_id],
        )
    ).id

    time_after_posting_first_spec = str(utcnow_naive())

    spectrum_id2 = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at=time_after_posting_first_spec,
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[434.7, 432.1, 435.3],
            group_ids=[group_id],
        )
    ).id

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        observed_before="2021-01-10T00:00:00",  # one year after 1st spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id1
    assert spectra[0].fluxes[0] == 234.3
    assert spectra[0].obj_id == public_source.id

    # test open ended range that includes second spectrum
    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        observed_after=time_after_posting_first_spec,
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id2
    assert spectra[0].fluxes[0] == 434.7
    assert spectra[0].obj_id == public_source.id

    # test open ended range that includes both spectra
    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        observed_after="2020-01-01T00:00:00",
    )
    assert len(spectra) == 2

    # test various date formats
    # can't parse this: 'T00:00:00&plus;00:00'
    dates = ["", "T00:00:00+00:00", "T00:00:00Z"]
    for d in dates:
        spectra = sp.fetch_spectra_query(
            group_ids=[group_id],
            observed_after=f"2020-01-15{d}",  # should get only second spectrum
        )
        assert len(spectra) == 1
        assert spectra[0].id == spectrum_id2


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
    sp = client(super_admin_token)

    # make a group that is unique to this test
    group_id = sp.post_group(
        GroupPost(
            name=str(uuid.uuid4()),
            group_admins=[super_admin_user.id],
        )
    ).id

    # post two spectra with very different properties
    spectrum_id1 = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at="2020-01-10T00:00:00",
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.3, 232.1, 235.3],
            group_ids=[group_id],
            followup_request_id=public_source_followup_request.id,
            assignment_id=public_assignment.id,
        )
    ).id

    spectrum_id2 = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at=str(utcnow_naive()),
            instrument_id=sedm.id,
            wavelengths=[664, 665, 666],
            fluxes=[434.7, 432.1, 435.3],
            group_ids=[group_id],
            followup_request_id=public_source_group2_followup_request.id,
        )
    ).id

    # test instrument IDs
    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        instrument_ids=[lris.id],  # should get only first spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id1

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        instrument_ids=[sedm.id],  # should get only second spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id2

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        instrument_ids=[lris.id, sedm.id],  # should get both
    )
    assert len(spectra) == 2

    with pytest.raises(SkyPortalError, match="Not all Instrument IDs") as err:
        sp.fetch_spectra_query(
            group_ids=[group_id],
            instrument_ids=[lris.id, sedm.id, lris.id * sedm.id],  # should fail
        )
    assert err.value.status_code == 400

    # raw api: intentionally malformed payload the typed client can't produce
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
    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        # should get only first spectrum
        followup_request_ids=[public_source_followup_request.id],
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id1

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        # should only get second spectrum
        followup_request_ids=[public_source_group2_followup_request.id],
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id2

    with pytest.raises(SkyPortalError, match="Not all FollowupRequest IDs") as err:
        sp.fetch_spectra_query(
            group_ids=[group_id],
            # should get error
            followup_request_ids=[public_source_group2_followup_request.id * 10],
        )
    assert err.value.status_code == 400

    with pytest.raises(SkyPortalError, match="Not all FollowupRequest IDs") as err:
        # should fail due to permission to see followup request
        client(comment_token).fetch_spectra_query(
            group_ids=[group_id],
            followup_request_ids=[public_source_group2_followup_request.id],
        )
    assert err.value.status_code == 400

    # test assignments
    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        assignment_ids=[public_assignment.id],  # should get only first spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id1

    with pytest.raises(SkyPortalError, match="Not all ClassicalAssignment IDs") as err:
        sp.fetch_spectra_query(
            group_ids=[group_id],
            assignment_ids=[public_assignment.id * 10],  # should fail
        )
    assert err.value.status_code == 400


def test_spectrum_filtering_origin_label_type(
    super_admin_user,
    super_admin_token,
    public_source,
    lris,
):
    sp = client(super_admin_token)

    # make a group that is unique to this test
    group_id = sp.post_group(
        GroupPost(
            name=str(uuid.uuid4()),
            group_admins=[super_admin_user.id],
        )
    ).id

    # post two spectra with very different properties
    custom_label = str(uuid.uuid4())
    spectrum_id1 = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at="2020-01-10T00:00:00",
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.3, 232.1, 235.3],
            group_ids=[group_id],
            label=custom_label,
            origin="Keck telescope",
        )
    ).id

    spectrum_id2 = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at=str(utcnow_naive()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[434.7, 432.1, 435.3],
            group_ids=[group_id],
            type="host",
            origin="Palomar 60 inch",
        )
    ).id

    # test origin
    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        origin=["Keck"],  # should get only first spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id1

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        origin=["Gemini", "VLT"],  # should get nothing
    )
    assert len(spectra) == 0

    # test label
    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        label=[custom_label],  # should get only first spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id1

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        label=["one", "two", "three"],  # should get nothing
    )
    assert len(spectra) == 0

    # test type
    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        spectrum_type=["source"],  # should get only first spectrum (default type)
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id1

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        spectrum_type=["host"],  # should get only second spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id2

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        spectrum_type=["host_center"],  # should get nothing
    )
    assert len(spectra) == 0

    with pytest.raises(
        SkyPortalError, match="not in list of allowed spectrum types"
    ) as err:
        sp.fetch_spectra_query(
            group_ids=[group_id],
            spectrum_type=["rainbow"],  # should get error, (allowed enum)
        )
    assert err.value.status_code == 400


def test_spectrum_filtering_comments(
    super_admin_user,
    super_admin_token,
    upload_data_token,
    comment_token,
    public_source,
    lris,
):
    sp = client(super_admin_token)

    # make a group that is unique to this test
    group_id = (
        client(upload_data_token)
        .post_group(
            GroupPost(
                name=str(uuid.uuid4()),
                # group_admins=[super_admin_user.id],
            )
        )
        .id
    )

    # post two spectra with very different properties
    spectrum_id1 = (
        client(upload_data_token)
        .post_spectrum(
            SpectrumPost(
                obj_id=public_source.id,
                observed_at="2020-01-10T00:00:00",
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[234.3, 232.1, 235.3],
                group_ids=[group_id],
            )
        )
        .id
    )

    comment_text = str(uuid.uuid4())
    client(comment_token).post_comment(
        spectrum_id1, comment_text, resource_type="spectra", group_ids=[group_id]
    )

    time.sleep(2)
    time_after_posting_first_spec = str(utcnow_naive())

    spectrum_id2 = (
        client(upload_data_token)
        .post_spectrum(
            SpectrumPost(
                obj_id=public_source.id,
                observed_at=time_after_posting_first_spec,
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[434.7, 432.1, 435.3],
                group_ids=[group_id],
            )
        )
        .id
    )

    sp.post_comment(
        spectrum_id2, "looks like Ia.", resource_type="spectra", group_ids=[group_id]
    )

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        comments_filter=[comment_text[10:20]],  # should get first spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id1

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        # should get second spectrum
        comments_filter_author=[super_admin_user.username[8:16]],
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id2

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        comments_filter_author=[str(uuid.uuid4())],  # should get nothing
    )
    assert len(spectra) == 0
    time_offset = (utcnow_naive() - datetime.datetime.now()) / datetime.timedelta(
        hours=1
    )

    comment_created_time = str(
        arrow.get(time_after_posting_first_spec)
        .shift(seconds=-1)
        .shift(hours=time_offset)
    )
    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        comments_filter_before=comment_created_time,  # should get first spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id1

    spectra = sp.fetch_spectra_query(
        group_ids=[group_id],
        comments_filter_after=comment_created_time,  # should get second spectrum
    )
    assert len(spectra) == 1
    assert spectra[0].id == spectrum_id2


def test_minimal_spectrum(
    super_admin_token,
    public_source,
    lris,
    public_assignment,
    public_source_followup_request,
):
    sp = client(super_admin_token)

    # make a group that is unique to this test
    group_id = sp.post_group(
        GroupPost(
            name=str(uuid.uuid4()),
            # group_admins=[super_admin_user.id],
        )
    ).id

    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at="2020-01-10T00:00:00",
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.3, 232.1, 235.3],
            group_ids=[group_id],
            followup_request_id=public_source_followup_request.id,
            assignment_id=public_assignment.id,
            origin=str(uuid.uuid4()),
            type="host",
            label=str(uuid.uuid4()),
            altdata={"one": 1, "two": 2},
        )
    ).id

    # post a comment and an annotation as well
    sp.post_comment(
        spectrum_id, str(uuid.uuid4()), resource_type="spectra", group_ids=[group_id]
    )

    sp.post_annotation(
        spectrum_id,
        "Kowalski",
        {
            "Gaia_Rp": 14.7,
            "Gaia_Bp": 15.2,
            "Gaia_G": 14.9,
            "period": 13.4,
        },
        resource_type="spectra",
        group_ids=[group_id],
    )

    # raw api: compares raw JSON key sets, which typed models normalize away
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

    # raw api: compares raw JSON key sets, which typed models normalize away
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

    # raw api: compares raw JSON key sets, which typed models normalize away
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


def test_include_original_file(upload_data_token, public_source, public_group, lris):
    sp = client(upload_data_token)

    # upload via the ASCII endpoint so original_file_string is populated
    ascii_content = "4000 0.01\n4500 0.02\n5000 0.005\n5500 0.006\n6000 0.01\n"
    spectrum_id = sp.post_spectrum_ascii(
        SpectrumAsciiPost(
            obj_id=str(public_source.id),
            observed_at="2020-02-01T00:00:00",
            instrument_id=lris.id,
            group_ids=[public_group.id],
            ascii=ascii_content,
            filename=f"{uuid.uuid4()}.ascii",
        )
    ).id

    # --- list endpoint (SpectrumHandler.get, multiple) ---
    # default: original_file_string omitted, rest of full payload intact
    spec = next(
        s
        for s in sp.fetch_spectra_query(obj_id=public_source.id)
        if s.id == spectrum_id
    )
    assert spec.original_file_string is None
    # full payload otherwise unchanged
    assert spec.wavelengths and spec.fluxes
    assert spec.original_file_filename is not None

    # includeOriginalFile=true: field present and equal to what was uploaded
    spec = next(
        s
        for s in sp.fetch_spectra_query(
            obj_id=public_source.id, include_original_file=True
        )
        if s.id == spectrum_id
    )
    assert spec.original_file_string == ascii_content

    # explicit includeOriginalFile=false behaves like the default
    spec = next(
        s
        for s in sp.fetch_spectra_query(
            obj_id=public_source.id, include_original_file=False
        )
        if s.id == spectrum_id
    )
    assert spec.original_file_string is None

    # --- single endpoint (SpectrumHandler.get, single) ---
    assert sp.fetch_spectrum(spectrum_id).original_file_string is None

    assert (
        sp.fetch_spectrum(spectrum_id, include_original_file=True).original_file_string
        == ascii_content
    )

    # --- object spectra endpoint (ObjSpectraHandler.get) ---
    spec = next(s for s in sp.fetch_spectra(public_source.id) if s.id == spectrum_id)
    assert spec.original_file_string is None

    spec = next(
        s
        for s in sp.fetch_spectra(public_source.id, include_original_file=True)
        if s.id == spectrum_id
    )
    assert spec.original_file_string == ascii_content


def test_token_user_get_range_spectrum(
    upload_data_token, public_source, public_group, lris
):
    sp = client(upload_data_token)

    # post two spectra at two different dates
    sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at="2020-01-10T00:00:00",
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    )

    sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[434.2, 432.1, 435.3],
            group_ids=[public_group.id],
        )
    )

    # test range that includes first spectrum
    spectra = sp.fetch_spectra_range(
        instrument_ids=[lris.id],
        min_date="2020-01-01T00:00:00",
        max_date="2020-01-15T00:00:00",
    )
    assert len(spectra) == 1
    assert spectra[0].fluxes[0] == 234.2
    assert spectra[0].obj_id == public_source.id

    # test open ended range that includes second spectrum
    spectra = sp.fetch_spectra_range(
        instrument_ids=[lris.id], min_date="2020-01-15T00:00:00"
    )
    assert len(spectra) == 1
    assert spectra[0].fluxes[0] == 434.2
    assert spectra[0].obj_id == public_source.id

    # test open ended range that includes both spectra
    spectra = sp.fetch_spectra_range(
        instrument_ids=[lris.id], min_date="2020-01-01T00:00:00"
    )
    assert len(spectra) == 2

    # test legal variations on input isot format
    # 2020-01-15
    spectra = sp.fetch_spectra_range(instrument_ids=[lris.id], min_date="2020-01-15")
    assert len(spectra) == 1
    assert spectra[0].fluxes[0] == 434.2
    assert spectra[0].obj_id == public_source.id

    # 2020-01-15T00:00:00+00:00
    # raw api: intentionally malformed query string ('&plus;' splits the param) the typed client can't produce
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
    spectra = sp.fetch_spectra_range(
        instrument_ids=[lris.id], min_date="2020-01-15T00:00:00Z"
    )
    assert len(spectra) == 1
    assert spectra[0].fluxes[0] == 434.2
    assert spectra[0].obj_id == public_source.id

    # test with no instrument ids
    spectra = sp.fetch_spectra_range(
        min_date="2020-01-01T00:00:00", max_date="2020-02-01"
    )
    assert len(spectra) == 1
    assert spectra[0].fluxes[0] == 234.2
    assert spectra[0].obj_id == public_source.id


def test_token_user_post_get_spectrum_data(
    upload_data_token, public_source, public_group, lris
):
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    ).id

    spectrum = sp.fetch_spectrum(spectrum_id)
    assert spectrum.fluxes[0] == 234.2
    assert spectrum.obj_id == public_source.id


def test_token_user_post_spectrum_no_instrument_id(
    upload_data_token, public_source, public_group
):
    # raw api: intentionally malformed payload the typed client can't produce
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
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source_two_groups.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids="all",
        )
    ).id

    spectrum = sp.fetch_spectrum(spectrum_id)
    assert spectrum.fluxes[0] == 234.2
    assert spectrum.obj_id == public_source_two_groups.id


def test_token_user_post_spectrum_no_access(
    view_only_token, public_source, public_group, lris
):
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_spectrum(
            SpectrumPost(
                obj_id=str(public_source.id),
                observed_at=str(datetime.datetime.now()),
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[234.2, 232.1, 235.3],
                group_ids=[public_group.id],
            )
        )
    assert err.value.status_code == 401


def test_token_user_update_spectrum(
    upload_data_token, public_source, public_group, lris
):
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    ).id

    assert sp.fetch_spectrum(spectrum_id).fluxes[0] == 234.2

    sp.update_spectrum(
        spectrum_id,
        SpectrumUpdate(
            fluxes=[222.2, 232.1, 235.3],
            observed_at=str(datetime.datetime.now()),
            wavelengths=[664, 665, 666],
            group_ids="all",
        ),
    )

    spectrum = sp.fetch_spectrum(spectrum_id)
    assert spectrum.fluxes[0] == 222.2
    # test that length of groups is greater than 1 after adding all groups to the spectrum
    assert len(spectrum.groups) > 1


def test_token_user_cannot_update_unowned_spectrum(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    ).id

    assert sp.fetch_spectrum(spectrum_id).fluxes[0] == 234.2

    with pytest.raises(SkyPortalError) as err:
        client(manage_sources_token).update_spectrum(
            spectrum_id,
            SpectrumUpdate(
                fluxes=[222.2, 232.1, 235.3],
                observed_at=str(datetime.datetime.now()),
                wavelengths=[664, 665, 666],
            ),
        )
    assert err.value.status_code == 401


def test_admin_can_update_unowned_spectrum_data(
    upload_data_token, super_admin_token, public_source, public_group, lris
):
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    ).id

    assert sp.fetch_spectrum(spectrum_id).fluxes[0] == 234.2

    client(super_admin_token).update_spectrum(
        spectrum_id,
        SpectrumUpdate(
            fluxes=[222.2, 232.1, 235.3],
            observed_at=str(datetime.datetime.now()),
            wavelengths=[664, 665, 666],
            group_ids=[2, 3],
        ),
    )

    spectrum = sp.fetch_spectrum(spectrum_id)
    assert spectrum.fluxes[0] == 222.2
    # check if length of groups is 4 after adding permission to two groups (groups with id 2 and 3) because two groups already have permission to this spectrum (groups with id 1405 and 1406)
    assert len(spectrum.groups) == 4


def test_spectrum_owner_id_is_unmodifiable(
    upload_data_token,
    super_admin_user,
    super_admin_token,
    public_source,
    public_group,
    lris,
):
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    ).id

    assert sp.fetch_spectrum(spectrum_id).fluxes[0] == 234.2

    # raw api: intentionally malformed payload the typed client can't produce
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
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    ).id

    spectrum = sp.fetch_spectrum(spectrum_id)
    assert spectrum.fluxes[0] == 234.2
    assert spectrum.obj_id == public_source.id

    with pytest.raises(SkyPortalError) as err:
        client(manage_sources_token).delete_spectrum(spectrum_id)
    assert err.value.status_code == 401


def test_user_can_delete_owned_spectrum_data(
    upload_data_token, public_source, public_group, lris
):
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    ).id

    spectrum = sp.fetch_spectrum(spectrum_id)
    assert spectrum.fluxes[0] == 234.2
    assert spectrum.obj_id == public_source.id

    sp.delete_spectrum(spectrum_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_spectrum(spectrum_id)
    assert err.value.status_code == 403


def test_admin_can_delete_unowned_spectrum_data(
    upload_data_token, super_admin_token, public_source, public_group, lris
):
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    ).id

    spectrum = sp.fetch_spectrum(spectrum_id)
    assert spectrum.fluxes[0] == 234.2
    assert spectrum.obj_id == public_source.id

    client(super_admin_token).delete_spectrum(spectrum_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_spectrum(spectrum_id)
    assert err.value.status_code == 403


def test_jsonify_spectrum_header(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    for filename in glob(f"{os.path.dirname(__file__)}/../../data/ZTF*.ascii.head"):
        with open(filename[:-5]) as f:
            parsed = client(upload_data_token).parse_spectrum_ascii(
                SpectrumAsciiParse(
                    fluxerr_column=(
                        3
                        if "ZTF20abpuxna_20200915_Keck1_v1.ascii" in filename
                        else 2
                        if "P60" in filename
                        else None
                    ),
                    ascii=f.read(),
                )
            )

        answer = yaml.safe_load(open(filename))

        # check the header serialization
        for key in answer:
            # special keys
            if key not in ["COMMENT", "END", "HISTORY"]:
                if isinstance(parsed.altdata[key], dict):
                    value = parsed.altdata[key]["value"]
                else:
                    value = parsed.altdata[key]
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
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
        )
    ).id

    assert len(sp.fetch_spectrum(spectrum_id).groups) == 1


def test_can_post_spectrum_empty_groups_list(
    upload_data_token, public_source, public_group, lris
):
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[],
        )
    ).id

    assert len(sp.fetch_spectrum(spectrum_id).groups) == 1


def test_jsonify_spectrum_data(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    for filename in glob(f"{os.path.dirname(__file__)}/../../data/ZTF*.ascii"):
        with open(filename) as f:
            parsed = client(upload_data_token).parse_spectrum_ascii(
                SpectrumAsciiParse(
                    fluxerr_column=(
                        3
                        if "ZTF20abpuxna_20200915_Keck1_v1.ascii" in filename
                        else 2
                        if "P60" in filename
                        else None
                    ),
                    ascii=f.read(),
                )
            )

        answer = np.genfromtxt(filename, dtype=float, encoding="ascii")

        if answer.shape[-1] == 2:
            np.testing.assert_allclose(
                np.asarray(parsed.wavelengths, dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(parsed.fluxes, dtype=float), answer[:, 1]
            )

        elif answer.shape[-1] == 3:
            np.testing.assert_allclose(
                np.asarray(parsed.wavelengths, dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(parsed.fluxes, dtype=float), answer[:, 1]
            )
            np.testing.assert_allclose(
                np.asarray(parsed.errors, dtype=float), answer[:, 2]
            )

        else:
            # this is the long one from Keck
            np.testing.assert_allclose(
                np.asarray(parsed.wavelengths, dtype=float), answer[:, 0]
            )
            np.testing.assert_allclose(
                np.asarray(parsed.fluxes, dtype=float), answer[:, 1]
            )
            np.testing.assert_allclose(
                np.asarray(parsed.errors, dtype=float), answer[:, 3]
            )


def test_upload_bad_spectrum_from_ascii_file(
    upload_data_token, manage_sources_token, public_source, public_group, lris
):
    for filename in glob(f"{os.path.dirname(__file__)}/../../data/ZTF*.ascii.bad"):
        with open(filename) as f:
            content = f.read()
            observed_at = str(datetime.datetime.now())

            with pytest.raises(SkyPortalError) as err:
                client(upload_data_token).post_spectrum_ascii(
                    SpectrumAsciiPost(
                        obj_id=str(public_source.id),
                        observed_at=observed_at,
                        instrument_id=lris.id,
                        group_ids=[public_group.id],
                        fluxerr_column=(
                            3
                            if "ZTF20abpuxna_20200915_Keck1_v1.ascii" in filename
                            else 2
                            if "P60" in filename
                            else None
                        ),
                        ascii=content,
                        filename=filename,
                    )
                )
            assert err.value.status_code == 400


def test_token_user_post_to_foreign_group_and_retrieve(
    upload_data_token, public_source_two_groups, public_group2, lris
):
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source_two_groups.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group2.id],
        )
    ).id

    sp.fetch_spectrum(spectrum_id)


def test_parse_integer_spectrum_ascii(upload_data_token):
    # raw api: asserts the server serializes wavelengths as floats in raw JSON, which pydantic coercion would mask
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
    sp = client(upload_data_token)
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
            reduced_by=[user.id],
            external_reducer="Test external reducer",
            observed_by=[user.id],
            external_observer="Test external observer",
            pi=[user.id],
            external_pi="Test external PI",
        )
    ).id

    spectrum = sp.fetch_spectrum(spectrum_id)
    assert spectrum.reducers[0].id == user.id
    assert spectrum.observers[0].id == user.id
    assert spectrum.pis[0].id == user.id
    assert spectrum.external_reducer == "Test external reducer"
    assert spectrum.external_observer == "Test external observer"
    assert spectrum.external_pi == "Test external PI"


def test_post_get_spectrum_type(upload_data_token, public_source, public_group, lris):
    sp = client(upload_data_token)

    # post this spectrum without a type (should default to "source")
    spectrum_id = sp.post_spectrum(
        SpectrumPost(
            obj_id=str(public_source.id),
            observed_at=str(datetime.datetime.now()),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    ).id

    assert sp.fetch_spectrum(spectrum_id).type == default_spectrum_type

    assert default_spectrum_type in ALLOWED_SPECTRUM_TYPES

    if len(ALLOWED_SPECTRUM_TYPES) > 1:
        new_allowed_types = list(ALLOWED_SPECTRUM_TYPES)
        new_allowed_types.remove(default_spectrum_type)

        spectrum_id = sp.post_spectrum(
            SpectrumPost(
                obj_id=str(public_source.id),
                observed_at=str(datetime.datetime.now()),
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[234.2, 232.1, 235.3],
                group_ids=[public_group.id],
                type=new_allowed_types[0],
            )
        ).id

        assert sp.fetch_spectrum(spectrum_id).type == new_allowed_types[0]


def test_post_wrong_spectrum_type(upload_data_token, public_source, public_group, lris):
    # post this spectrum with the wrong type
    with pytest.raises(SkyPortalError, match="Must be one of: ") as err:
        client(upload_data_token).post_spectrum(
            SpectrumPost(
                obj_id=str(public_source.id),
                observed_at=str(datetime.datetime.now()),
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[234.2, 232.1, 235.3],
                group_ids=[public_group.id],
                type=str(uuid.uuid4()),
            )
        )
    assert err.value.status_code == 400


def test_bulk_spectra(
    super_admin_user, super_admin_token, public_source, public_group, lris
):
    sp = client(super_admin_token)
    sp.post_spectrum(
        SpectrumPost(
            obj_id=public_source.id,
            observed_at="2020-01-10T00:00:00",
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.3, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    )

    def check(result):
        source_ids = [s.id for s in result.sources]
        assert public_source.id in source_ids
        src = next(s for s in result.sources if s.id == public_source.id)
        # Phase anchors are always present (values may be null without a PhotStat).
        for key in ("redshift", "first_detected_mjd", "peak_mjd", "tns_discovery_date"):
            assert hasattr(src, key)
        spectra = [sp for sp in result.spectra if sp.obj_id == public_source.id]
        assert len(spectra) >= 1
        assert spectra[0].wavelengths[0] == 664
        assert spectra[0].fluxes[0] == 234.3
        assert spectra[0].observed_at is not None

    # Select by explicit object list.
    check(sp.post_spectra_bulk(obj_ids=[public_source.id]))

    # Select by group.
    check(sp.post_spectra_bulk(group_id=public_group.id))
