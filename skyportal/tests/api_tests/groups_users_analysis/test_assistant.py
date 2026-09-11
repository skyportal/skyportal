import uuid

from skyportal.model_util import create_token
from skyportal.models import AssistantMessage, DBSession
from skyportal.tests import api, assert_api, assert_api_fail


def _token(user):
    return create_token(ACLs=[], user_id=user.id, name=str(uuid.uuid4()))


def _seed(user_id, channel, text, system=False):
    message = AssistantMessage(
        user_id=user_id, channel=channel, text=text, system=system
    )
    DBSession().add(message)
    DBSession().commit()
    return message.id


def test_read_a_conversation_oldest_first(user):
    token_id = _token(user)
    channel = str(uuid.uuid4())
    _seed(user.id, channel, "what is this source?")
    _seed(user.id, channel, "An X-ray flash.", system=True)

    status, data = api(
        "GET", "assistant/messages", params={"channel": channel}, token=token_id
    )
    assert_api(status, data)
    assert [(m["text"], m["system"]) for m in data["data"]] == [
        ("what is this source?", False),
        ("An X-ray flash.", True),
    ]


def test_the_unnamed_conversation_is_its_own(user):
    token_id = _token(user)
    channel = str(uuid.uuid4())
    _seed(user.id, None, "asked from nowhere")
    _seed(user.id, channel, "asked in a chat")

    status, data = api("GET", "assistant/messages", token=token_id)
    assert_api(status, data)
    assert [m["text"] for m in data["data"]] == ["asked from nowhere"]


def test_another_user_sees_nothing(user, user_group2):
    channel = str(uuid.uuid4())
    _seed(user.id, channel, "what is this source?")

    other_token = _token(user_group2)
    status, data = api(
        "GET", "assistant/messages", params={"channel": channel}, token=other_token
    )
    assert_api(status, data)
    assert data["data"] == []

    status, data = api(
        "GET",
        "assistant/conversations",
        token=other_token,
    )
    assert_api(status, data)
    assert channel not in data["data"]

    status, data = api(
        "DELETE",
        "assistant/conversations",
        params={"channel": channel},
        token=other_token,
    )
    assert_api_fail(status, data, expected_error_partial="Invalid channel")


def test_conversations_lists_only_the_named_ones(user):
    token_id = _token(user)
    channel = str(uuid.uuid4())
    _seed(user.id, None, "asked from nowhere")
    _seed(user.id, channel, "asked in a chat")

    status, data = api("GET", "assistant/conversations", token=token_id)
    assert_api(status, data)
    assert data["data"] == [channel]


def test_rename_a_conversation(user):
    token_id = _token(user)
    channel = str(uuid.uuid4())
    renamed = str(uuid.uuid4())
    _seed(user.id, channel, "what is this source?")
    _seed(user.id, channel, "An X-ray flash.", system=True)

    status, data = api(
        "PATCH",
        "assistant/conversations",
        data={"name": renamed},
        params={"channel": channel},
        token=token_id,
    )
    assert_api(status, data)

    status, data = api(
        "GET", "assistant/messages", params={"channel": renamed}, token=token_id
    )
    assert_api(status, data)
    assert len(data["data"]) == 2

    status, data = api(
        "GET", "assistant/messages", params={"channel": channel}, token=token_id
    )
    assert_api(status, data)
    assert data["data"] == []


def test_rename_rejects_a_name_already_in_use(user):
    token_id = _token(user)
    channel = str(uuid.uuid4())
    taken = str(uuid.uuid4())
    _seed(user.id, channel, "asked here")
    _seed(user.id, taken, "asked there")

    status, data = api(
        "PATCH",
        "assistant/conversations",
        data={"name": taken},
        params={"channel": channel},
        token=token_id,
    )
    assert_api_fail(status, data, expected_error_partial="already exists")


def test_rename_needs_a_channel_and_a_name(user):
    token_id = _token(user)
    channel = str(uuid.uuid4())
    _seed(user.id, channel, "asked here")

    status, data = api(
        "PATCH",
        "assistant/conversations",
        data={"name": str(uuid.uuid4())},
        token=token_id,
    )
    assert_api_fail(status, data, expected_error_partial="`channel` must be provided")

    status, data = api(
        "PATCH",
        "assistant/conversations",
        data={"name": "   "},
        params={"channel": channel},
        token=token_id,
    )
    assert_api_fail(status, data, expected_error_partial="`name` must not be empty")

    status, data = api(
        "PATCH",
        "assistant/conversations",
        data={"name": str(uuid.uuid4())},
        params={"channel": str(uuid.uuid4())},
        token=token_id,
    )
    assert_api_fail(status, data, expected_error_partial="Invalid channel")


def test_delete_a_conversation_leaves_the_others(user):
    token_id = _token(user)
    channel = str(uuid.uuid4())
    kept = str(uuid.uuid4())
    _seed(user.id, channel, "asked here")
    _seed(user.id, kept, "asked there")

    status, data = api(
        "DELETE",
        "assistant/conversations",
        params={"channel": channel},
        token=token_id,
    )
    assert_api(status, data)

    status, data = api("GET", "assistant/conversations", token=token_id)
    assert_api(status, data)
    assert data["data"] == [kept]


def test_delete_needs_a_channel_that_exists(user):
    token_id = _token(user)

    status, data = api("DELETE", "assistant/conversations", token=token_id)
    assert_api_fail(status, data, expected_error_partial="`channel` must be provided")

    status, data = api(
        "DELETE",
        "assistant/conversations",
        params={"channel": str(uuid.uuid4())},
        token=token_id,
    )
    assert_api_fail(status, data, expected_error_partial="Invalid channel")


def test_asking_needs_a_configured_assistant(user):
    token_id = _token(user)
    status, data = api(
        "POST",
        "assistant/messages",
        data={"text": "what is this source?"},
        token=token_id,
    )
    assert_api_fail(status, data, expected_error_partial="No assistant is configured")

    status, data = api("GET", "assistant/messages", token=token_id)
    assert_api(status, data)
    assert data["data"] == []
