from skyportal.handlers.api.hermes.hermes import (
    create_payload_and_header,
    validate_payload_and_header,
)
from skyportal.tests import api


def test_hermes_payload_creation_and_validation(public_obj):
    data = {
        "hermes_token": "BadToken",
        "topic": "hermes.test",
        "title": "Title test",
        "submitter": "Test user",
    }

    payload, header = create_payload_and_header(public_obj, data)

    assert isinstance(payload, str)
    assert header == {
        "Authorization": f"Token BadToken",
        "Content-Type": "application/json",
    }

    try:
        validate_payload_and_header(payload, header)
    except ValueError as e:
        assert str(e) == 'Failed to validate payload: 403: {"detail":"Invalid token."}'


def test_hermes_publishing(public_obj, super_admin_token):
    assert public_obj.photometry is not None

    data = {
        "hermes_token": "BadToken",
        "topic": "hermes.test",
        "title": "Title test",
        "submitter": "Test user",
    }

    try:
        status, data = api(
            "POST", f"hermes/{public_obj.id}", data, token=super_admin_token
        )
    except ValueError as e:
        assert str(e) == 'Failed to validate payload: 403: {"detail":"Invalid token."}'
