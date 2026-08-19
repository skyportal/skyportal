import pytest
from skyportal_py import SkyPortalError
from skyportal_py.allocations import AllocationPost, AllocationUpdate
from skyportal_py.followup_requests import FollowupRequestPost

from skyportal.tests import client


def test_super_user_post_allocation(
    sedm, public_group, public_group2, super_admin_token
):
    sp = client(super_admin_token)
    request_data = AllocationPost(
        group_id=public_group.id,
        instrument_id=sedm.id,
        pi="Shri Kulkarni",
        hours_allocated=200,
        validity_ranges=[
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        proposal_id="COO-2020A-P01",
        default_share_group_ids=[public_group.id, public_group2.id],
    )

    id = sp.post_allocation(request_data).id

    allocation = sp.fetch_allocation(id)

    for key, value in request_data.model_dump(exclude_none=True).items():
        assert getattr(allocation, key) == value


def test_super_user_modify_allocation(sedm, public_group, super_admin_token):
    sp = client(super_admin_token)
    request_data = AllocationPost(
        group_id=public_group.id,
        instrument_id=sedm.id,
        pi="Shri Kulkarni",
        hours_allocated=200,
        validity_ranges=[
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        proposal_id="COO-2020A-P01",
    )

    id = sp.post_allocation(request_data).id

    allocation = sp.fetch_allocation(id)

    for key, value in request_data.model_dump(exclude_none=True).items():
        assert getattr(allocation, key) == value

    request2_data = AllocationUpdate(proposal_id="COO-2020A-P02")

    sp.update_allocation(id, request2_data)

    allocation = sp.fetch_allocation(id)

    expected = request_data.model_dump(exclude_none=True)
    expected.update(request2_data.model_dump(exclude_none=True))
    for key, value in expected.items():
        assert getattr(allocation, key) == value


def test_read_only_user_cannot_get_unowned_allocation(
    view_only_token, super_admin_token, sedm, public_group2
):
    sp = client(super_admin_token)
    request_data = AllocationPost(
        group_id=public_group2.id,
        instrument_id=sedm.id,
        pi="Shri Kulkarni",
        hours_allocated=200,
        validity_ranges=[
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        proposal_id="COO-2020A-P01",
    )

    id = sp.post_allocation(request_data).id

    allocation = sp.fetch_allocation(id)

    for key, value in request_data.model_dump(exclude_none=True).items():
        assert getattr(allocation, key) == value

    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_allocation(id)
    assert err.value.status_code == 400


def test_read_only_user_get_invalid_allocation_id(view_only_token):
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_allocation(-1)
    assert err.value.status_code == 400


def test_delete_allocation_cascades_to_requests(
    public_group, public_source, super_admin_token, sedm
):
    sp = client(super_admin_token)
    allocation_id = sp.post_allocation(
        AllocationPost(
            group_id=public_group.id,
            instrument_id=sedm.id,
            pi="Shri Kulkarni",
            hours_allocated=200,
            validity_ranges=[
                {
                    "start_date": "2021-02-27T00:00:00.000Z",
                    "end_date": "3021-07-20T00:00:00.000Z",
                }
            ],
            proposal_id="COO-2020A-P01",
        )
    ).id

    request_id = sp.post_followup_request(
        FollowupRequestPost(
            allocation_id=allocation_id,
            obj_id=public_source.id,
            payload={
                "priority": 5,
                "start_date": "3010-09-01",
                "end_date": "3012-09-01",
                "observation_type": "IFU",
                "exposure_time": 300,
                "maximum_airmass": 2,
                "maximum_fwhm": 1.2,
            },
        )
    ).id

    sp.fetch_followup_request(request_id)

    sp.delete_allocation(allocation_id)

    with pytest.raises(
        SkyPortalError, match="Could not retrieve followup request"
    ) as err:
        sp.fetch_followup_request(request_id)
    assert err.value.status_code == 400


def test_allocation_comment(public_group, public_source, super_admin_token, sedm):
    sp = client(super_admin_token)
    # Create and post an allocation
    allocation_id = sp.post_allocation(
        AllocationPost(
            group_id=public_group.id,
            instrument_id=sedm.id,
            pi="Shri Kulkarni",
            hours_allocated=200,
            validity_ranges=[
                {
                    "start_date": "2021-02-27T00:00:00.000Z",
                    "end_date": "3021-07-20T00:00:00.000Z",
                }
            ],
            proposal_id="COO-2020A-P01",
        )
    ).id

    # Post a followup request with the allocation id and no comment
    request_id = sp.post_followup_request(
        FollowupRequestPost(
            allocation_id=allocation_id,
            obj_id=public_source.id,
            payload={
                "priority": 5,
                "start_date": "3010-09-01",
                "end_date": "3012-09-01",
                "observation_type": "IFU",
                "exposure_time": 300,
                "maximum_airmass": 2,
                "maximum_fwhm": 1.2,
            },
        )
    ).id

    # Check that the comment on the followup request is empty
    assert sp.fetch_followup_request(request_id).comment is None

    # Put a comment on the followup request
    sp.post_followup_request_comment(request_id, "This is a test comment")

    # Check that the comment is now set
    assert sp.fetch_followup_request(request_id).comment == "This is a test comment"

    # Put an empty comment on the followup request
    sp.post_followup_request_comment(request_id, "")

    # Check that the comment is now set to empty
    assert sp.fetch_followup_request(request_id).comment is None
