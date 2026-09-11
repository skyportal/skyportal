import uuid

from skyportal.model_util import create_token
from skyportal.tests import api
from skyportal.utils.assistant import SERVICE_TOKEN_PREFIX


def test_add_and_delete_tokens(super_admin_token, user):
    token_name = str(uuid.uuid4())

    data = {
        "acls": ["Classify", "Annotate", "Comment"],
        "user_id": user.id,
        "name": token_name,
    }

    status, data = api("POST", "internal/tokens", token=super_admin_token, data=data)
    assert status == 200
    token_id = data["data"]["token_id"]

    status, data = api("GET", "internal/tokens", token=super_admin_token)
    assert status == 200
    assert any(token["id"] == token_id for token in data["data"])

    status, data = api("DELETE", f"internal/tokens/{token_id}", token=super_admin_token)
    assert status == 200

    status, data = api("GET", "internal/tokens", token=super_admin_token)
    assert status == 200
    assert all(token["id"] != token_id for token in data["data"])


def test_multiple_tokens(super_admin_token, user, annotation_token):
    token_name_1 = str(uuid.uuid4())

    data = {
        "acls": ["Classify", "Annotate", "Comment"],
        "user_id": user.id,
        "name": token_name_1,
    }

    status, data = api("POST", "internal/tokens", token=super_admin_token, data=data)
    assert status == 200

    token_name_2 = str(uuid.uuid4())
    data = {
        "acls": ["Classify", "Annotate", "Comment"],
        "user_id": user.id,
        "name": token_name_2,
    }

    status, data = api("POST", "internal/tokens", token=super_admin_token, data=data)
    assert status == 200

    token_name_3 = str(uuid.uuid4())
    data = {
        "acls": ["Classify", "Annotate", "Comment"],
        "user_id": user.id,
        "name": token_name_3,
    }

    status, data = api("POST", "internal/tokens", token=annotation_token, data=data)
    assert status == 400


def test_the_service_token_prefix_is_reserved(super_admin_token, user):
    status, data = api(
        "POST",
        "internal/tokens",
        token=super_admin_token,
        data={
            "acls": ["Comment"],
            "user_id": user.id,
            "name": f"{SERVICE_TOKEN_PREFIX}{uuid.uuid4().hex}",
        },
    )
    assert status != 200
    assert SERVICE_TOKEN_PREFIX in data["message"]

    status, data = api(
        "POST",
        "internal/tokens",
        token=super_admin_token,
        data={"acls": ["Comment"], "user_id": user.id, "name": str(uuid.uuid4())},
    )
    assert status == 200
    token_id = data["data"]["token_id"]

    status, data = api(
        "PUT",
        f"internal/tokens/{token_id}",
        token=super_admin_token,
        data={"name": f"{SERVICE_TOKEN_PREFIX}{uuid.uuid4().hex}"},
    )
    assert status != 200
    assert SERVICE_TOKEN_PREFIX in data["message"]


def test_service_tokens_are_hidden_from_the_profile(user):
    own = create_token(ACLs=[], user_id=user.id, name=str(uuid.uuid4()))
    create_token(
        ACLs=[], user_id=user.id, name=f"{SERVICE_TOKEN_PREFIX}{uuid.uuid4().hex}"
    )

    status, data = api("GET", "internal/profile", token=own)
    assert status == 200
    assert [token["id"] for token in data["data"]["tokens"]] == [own]
