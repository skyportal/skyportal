from skyportal.handlers.api.hermes.hermes import create_payload_and_header


def test_hermes_payload_creation_and_validation(public_obj):
    data = {
        "hermes_token": "Bad token",
        "topic": "hermes.test",
        "title": "Title test",
        "submitter": "Test user",
    }

    try:
        payload, header = create_payload_and_header(public_obj, data)
    except ValueError as e:
        assert (
            str(e)
            == 'Failed to validate payload: 403: {"detail":"Invalid token header. Token string should not contain spaces."}'
        )

    data["hermes_token"] = "BadToken"

    try:
        payload, header = create_payload_and_header(public_obj, data)
    except ValueError as e:
        assert str(e) == 'Failed to validate payload: 403: {"detail":"Invalid token."}'
