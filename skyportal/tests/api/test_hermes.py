from skyportal.tests import api


def test_hermes_publishing(public_obj, super_admin_token):
    assert public_obj.photometry is not None

    data = {
        "hermes_token": "TOKEN",
        "topic": "hermes.test",
        "title": "Title test",
        "submitter": "Test user",
    }

    status, data = api("POST", f"hermes/{public_obj.id}", data, token=super_admin_token)
    print(status)
    print(data)
    assert status == 200
    assert data["status"] == "success"
