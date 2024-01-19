from skyportal.tests import api
from datetime import timedelta, datetime
import uuid
import time


def test_post_and_verify_recurring_api(
    view_only_token, public_group, super_admin_token
):
    next_call = datetime.utcnow() + timedelta(seconds=1)
    obj_id = str(uuid.uuid4())

    request_data = {
        "next_call": next_call.strftime("%Y-%m-%dT%H:%M:%S"),
        "call_delay": 0.001,
        "method": "POST",
        "endpoint": "sources",
        "payload": {
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
    }

    endpoint = "recurring_api"
    status, data = api(
        'POST',
        endpoint,
        data=request_data,
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    recurring_api_id = data["data"]["id"]

    endpoint = f"recurring_api/{recurring_api_id}"
    status, data = api(
        'GET',
        endpoint,
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    endpoint = f"sources/{obj_id}"
    n_retries = 0
    while n_retries < 10:
        status, data = api(
            'GET',
            endpoint,
            token=view_only_token,
        )
        if data['status'] == 'success':
            break
        time.sleep(15)
        n_retries += 1
    assert n_retries < 10
    assert status == 200
