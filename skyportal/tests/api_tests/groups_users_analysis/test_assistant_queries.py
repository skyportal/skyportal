import uuid

from skyportal.model_util import create_token
from skyportal.tests import api, assert_api, assert_api_fail


def _token(user):
    return create_token(ACLs=[], user_id=user.id, name=str(uuid.uuid4()))


def _find(rows, query_id):
    return next((r for r in rows if r["id"] == query_id), None)


def test_create_list_subscribe_unsubscribe_delete(user, public_group):
    token = _token(user)
    status, data = api(
        "POST",
        "assistant_queries",
        data={
            "name": "FLARE triage",
            "group_id": public_group.id,
            "prompt": "Triage this FLARE classification.",
            "analysis_service_match": "flare",
        },
        token=token,
    )
    assert_api(status, data)
    query_id = data["data"]["id"]

    # It is visible to the group member, unsubscribed, owned by them.
    status, data = api("GET", "assistant_queries", token=token)
    assert_api(status, data)
    row = _find(data["data"], query_id)
    assert row is not None
    assert row["subscribed"] is False
    assert row["subscriber_count"] == 0
    assert row["is_owner"] is True
    assert row["group_name"] == public_group.name

    # Subscribe -> reflected in the listing.
    status, data = api(
        "POST", f"assistant_queries/{query_id}/subscription", token=token
    )
    assert_api(status, data)
    status, data = api("GET", "assistant_queries", token=token)
    row = _find(data["data"], query_id)
    assert row["subscribed"] is True and row["subscriber_count"] == 1

    # Subscribing again is idempotent.
    status, data = api(
        "POST", f"assistant_queries/{query_id}/subscription", token=token
    )
    assert_api(status, data)
    status, data = api("GET", "assistant_queries", token=token)
    assert _find(data["data"], query_id)["subscriber_count"] == 1

    # Unsubscribe.
    status, data = api(
        "DELETE", f"assistant_queries/{query_id}/subscription", token=token
    )
    assert_api(status, data)
    status, data = api("GET", "assistant_queries", token=token)
    row = _find(data["data"], query_id)
    assert row["subscribed"] is False and row["subscriber_count"] == 0

    # Delete.
    status, data = api("DELETE", f"assistant_queries/{query_id}", token=token)
    assert_api(status, data)
    status, data = api("GET", "assistant_queries", token=token)
    assert _find(data["data"], query_id) is None


def test_owner_can_edit_query(user, public_group):
    token = _token(user)
    status, data = api(
        "POST",
        "assistant_queries",
        data={
            "name": "before",
            "group_id": public_group.id,
            "prompt": "old prompt",
            "analysis_service_match": "flare",
        },
        token=token,
    )
    assert_api(status, data)
    query_id = data["data"]["id"]

    status, data = api(
        "PATCH",
        f"assistant_queries/{query_id}",
        data={"name": "after", "prompt": "new prompt", "dry_run": True},
        token=token,
    )
    assert_api(status, data)

    status, data = api("GET", "assistant_queries", token=token)
    row = _find(data["data"], query_id)
    assert row["name"] == "after"
    assert row["prompt"] == "new prompt"
    assert row["dry_run"] is True
    # Untouched fields keep their values.
    assert row["analysis_service_match"] == "flare"

    api("DELETE", f"assistant_queries/{query_id}", token=token)


def test_cannot_create_in_a_group_youre_not_in(user, public_group2):
    token = _token(user)
    status, data = api(
        "POST",
        "assistant_queries",
        data={
            "name": "sneaky",
            "group_id": public_group2.id,
            "prompt": "triage",
        },
        token=token,
    )
    assert_api_fail(status, data, 403)
