from skyportal_py.followup_requests import FollowupRequestPost

from skyportal.tests import client


def test_reprioritize_followup_request(
    public_group_generic_allocation,
    public_source,
    upload_data_token,
    gcn_GW190425,
):
    localization_id = gcn_GW190425.localizations[0].id

    sp = client(upload_data_token)
    id = sp.post_followup_request(
        FollowupRequestPost(
            allocation_id=public_group_generic_allocation.id,
            obj_id=public_source.id,
            payload={
                "priority": 1,
                "start_date": "3010-09-01",
                "end_date": "3012-09-01",
                "observation_choices": public_group_generic_allocation.instrument.to_dict()[
                    "filters"
                ],
                "exposure_time": 300,
                "exposure_counts": 1,
                "maximum_airmass": 2,
                "minimum_lunar_distance": 30,
            },
        )
    ).id

    sp.update_followup_request_prioritization(
        request_ids=[id],
        priority_type="localization",
        localization_id=localization_id,
    )

    followup_request = sp.fetch_followup_request(id)
    assert followup_request.payload["priority"] == 5
