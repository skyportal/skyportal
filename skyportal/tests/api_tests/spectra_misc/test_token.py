import uuid

import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import client


def test_add_and_delete_tokens(super_admin_token, user):
    sp = client(super_admin_token)
    token_name = str(uuid.uuid4())

    token_id = sp.post_token(
        token_name, ["Classify", "Annotate", "Comment"], user_id=user.id
    ).token_id

    assert any(token.id == token_id for token in sp.fetch_tokens())

    sp.delete_token(token_id)

    assert all(token.id != token_id for token in sp.fetch_tokens())


def test_multiple_tokens(super_admin_token, user, annotation_token):
    sp = client(super_admin_token)
    acls = ["Classify", "Annotate", "Comment"]

    sp.post_token(str(uuid.uuid4()), acls, user_id=user.id)
    sp.post_token(str(uuid.uuid4()), acls, user_id=user.id)

    with pytest.raises(SkyPortalError) as err:
        client(annotation_token).post_token(str(uuid.uuid4()), acls, user_id=user.id)
    assert err.value.status_code == 400
