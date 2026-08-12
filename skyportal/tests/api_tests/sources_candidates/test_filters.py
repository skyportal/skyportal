import uuid

from skyportal.tests import api


def test_filter_list(view_only_token, public_filter):
    status, data = api("GET", "filters", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert all(k in data["data"][0] for k in ["name", "group_id", "stream_id"])


def test_token_user_retrieving_filter(view_only_token, public_filter):
    status, data = api("GET", f"filters/{public_filter.id}", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert all(k in data["data"] for k in ["name", "group_id", "stream_id"])


def test_token_user_update_filter(manage_groups_token, public_filter):
    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}",
        data={"name": "new_name"},
        token=manage_groups_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"filters/{public_filter.id}", token=manage_groups_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["name"] == "new_name"


def test_cannot_update_filter_group_stream(view_only_token, public_filter):
    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}",
        data={"group_id": 0},
        token=view_only_token,
    )
    assert status == 401
    assert data["status"] == "error"

    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}",
        data={"stream_id": 0},
        token=view_only_token,
    )
    assert status == 401
    assert data["status"] == "error"


def test_token_user_post_delete_filter(
    manage_groups_token, group_with_stream, public_stream
):
    status, data = api(
        "POST",
        "filters",
        data={
            "name": str(uuid.uuid4()),
            "stream_id": public_stream.id,
            "group_id": group_with_stream.id,
        },
        token=manage_groups_token,
    )
    assert status == 200
    filter_id = data["data"]["id"]

    status, data = api("GET", f"filters/{filter_id}", token=manage_groups_token)
    assert status == 200
    assert data["data"]["id"] == filter_id

    status, data = api("DELETE", f"filters/{filter_id}", token=manage_groups_token)
    assert status == 200

    status, data = api("GET", f"filters/{filter_id}", token=manage_groups_token)
    assert status == 400
    assert "Cannot find a filter with ID" in data["message"]


def test_post_filter_with_unauthorized_stream(
    manage_groups_token, group_with_stream, public_stream
):
    status, data = api(
        "POST",
        "filters",
        data={
            "name": str(uuid.uuid4()),
            "stream_id": public_stream.id - 1,
            "group_id": group_with_stream.id,
        },
        token=manage_groups_token,
    )
    assert status in [401, 500]


def _force_active(broker_id):
    """Activate a credential-gated broker without the live connection check."""
    import sqlalchemy as sa

    from skyportal.models import Broker, DBSession

    DBSession().execute(
        sa.update(Broker).where(Broker.id == broker_id).values(active=True)
    )
    DBSession().commit()


def _mark_broker_managed(filter_id, broker_id):
    """Point a filter at a broker the way BOOM filter creation does."""
    import sqlalchemy as sa
    from sqlalchemy.orm.attributes import flag_modified

    from skyportal.models import DBSession, Filter

    f = DBSession().scalars(sa.select(Filter).where(Filter.id == filter_id)).first()
    f.altdata = {"boom": {"filter_id": "boom-test-id"}}
    f.broker_id = broker_id
    flag_modified(f, "altdata")
    DBSession().commit()


def test_rename_requires_group_admin(upload_data_token, public_filter):
    """A rename is an admin action even for a user who may otherwise post data."""
    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}",
        data={"name": f"nope_{uuid.uuid4().hex[:8]}"},
        token=upload_data_token,
    )
    assert status == 403, data
    assert "group admin" in data["message"]


def test_rename_is_blocked_when_the_broker_rename_fails(
    super_admin_token, public_filter
):
    """The local name must not drift from the broker's.

    The broker here is unreachable, so the propagation attempt fails -- and that
    has to abort the whole rename rather than leaving the two names disagreeing.
    """
    status, data = api(
        "POST",
        "brokers",
        data={
            "name": str(uuid.uuid4()),
            "broker_classname": "BOOMBROKER",
            "altdata": {"host": "boom.invalid", "username": "x", "password": "y"},
        },
        token=super_admin_token,
    )
    assert status == 200, data
    broker_id = data["data"]["id"]
    _force_active(broker_id)

    status, data = api("GET", f"filters/{public_filter.id}", token=super_admin_token)
    original_name = data["data"]["name"]

    _mark_broker_managed(public_filter.id, broker_id)

    new_name = f"renamed_{uuid.uuid4().hex[:8]}"
    status, data = api(
        "PATCH",
        f"filters/{public_filter.id}",
        data={"name": new_name},
        token=super_admin_token,
    )
    assert status == 400, data
    assert "rename" in data["message"].lower()

    status, data = api("GET", f"filters/{public_filter.id}", token=super_admin_token)
    assert data["data"]["name"] == original_name, "local rename outlived the failure"
