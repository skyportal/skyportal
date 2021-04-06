from skyportal.tests import api


def test_invite_new_user(super_admin_token, public_stream, public_group):
    status, _ = api(
        "POST",
        "invitations",
        data={
            "userEmail": "string",
            "streamIDs": [public_stream.id],
            "groupIDs": [public_group.id],
            "groupAdmin": ["true"],
        },
        token=super_admin_token,
    )
    assert status == 200
