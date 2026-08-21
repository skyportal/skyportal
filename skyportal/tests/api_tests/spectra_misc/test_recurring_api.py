import json
import time
import uuid
from datetime import timedelta

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.recurring_apis import RecurringAPIPost

from skyportal.tests import client

from ....utils.naive_datetime import utcnow_naive


def test_post_and_verify_recurring_api(
    view_only_token, public_group, super_admin_token
):
    next_call = utcnow_naive() + timedelta(seconds=1)
    obj_id = str(uuid.uuid4())

    sp = client(super_admin_token)
    request_data = {
        "next_call": next_call.strftime("%Y-%m-%dT%H:%M:%S"),
        "call_delay": 0.001,
        "method": "POST",
        "endpoint": "sources",
        "payload": "{Test incorrect payload}",
    }

    with pytest.raises(SkyPortalError, match="payload must be a valid JSON string"):
        sp.post_recurring_api(RecurringAPIPost(**request_data))

    request_data["payload"] = json.dumps(
        {
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "group_ids": [public_group.id],
        }
    )

    recurring_api_id = sp.post_recurring_api(RecurringAPIPost(**request_data)).id

    sp.fetch_recurring_api(recurring_api_id)

    source = None
    n_retries = 0
    while n_retries < 10:
        try:
            source = client(view_only_token).fetch_source(obj_id)
            break
        except SkyPortalError:
            time.sleep(15)
            n_retries += 1
    assert n_retries < 10
    assert source is not None
