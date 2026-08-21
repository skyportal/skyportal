import uuid

import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import client


def test_obj_photometry(upload_data_token, public_source):
    sp = client(upload_data_token)
    sp.fetch_photometry(public_source.id)

    obj_id = str(uuid.uuid4())

    # try a non-existent source
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_photometry(obj_id)
    assert err.value.status_code == 403
    assert (
        str(err.value)
        == f"Insufficient permissions for User {upload_data_token} to read Obj {obj_id}"
    )
