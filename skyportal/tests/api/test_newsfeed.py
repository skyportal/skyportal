import uuid

from skyportal.tests import api


def test_token_user_retrieving_source_without_nested(
    view_only_token, public_group, upload_data_token
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 235.22,
            "dec": -23.33,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    params = {'numItems': 100}
    status, data = api('GET', 'newsfeed', token=view_only_token, params=params)

    assert status == 200
    data = data['data']
    assert any([d['type'] == 'source' for d in data])
    assert any([d['message'] == 'New source saved' for d in data])
    assert any([d['source_id'] == obj_id for d in data])
