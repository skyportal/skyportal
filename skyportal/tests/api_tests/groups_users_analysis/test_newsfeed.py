import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.sources import SourcePost

from skyportal.tests import client


def test_retrieve_newsfeed(view_only_token, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=235.22,
            dec=-23.33,
            redshift=3,
            group_ids=[public_group.id],
        )
    )

    items = client(view_only_token).fetch_news_feed(num_items=1000)
    assert any(d.type == "source" for d in items)
    assert any(d.message == "New source saved" for d in items)
    assert any(d.source_id == obj_id for d in items)


def test_fail_newsfeed_request_too_many(
    view_only_token,
):
    with pytest.raises(
        SkyPortalError, match="numItems should be no larger than 1000"
    ) as err:
        client(view_only_token).fetch_news_feed(num_items=1001)
    assert err.value.status_code == 400
