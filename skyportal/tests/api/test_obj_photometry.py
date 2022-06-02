import uuid

from skyportal.tests import api


def test_obj_photometry(upload_data_token, public_source):
    status, data = api(
        "GET",
        f"sources/{public_source.id}/photometry",
        token=upload_data_token,
    )
    assert status == 200

    obj_id = str(uuid.uuid4())

    # try a non-existent source
    status, data = api(
        "GET",
        f"sources/{obj_id}/photometry",
        token=upload_data_token,
    )
    assert status == 400
    assert (
        data['message']
        == f'Insufficient permissions for User {upload_data_token} to read Obj {obj_id}'
    )
