import uuid

import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import client


def test_super_obj_create_and_retrieve(
    super_admin_token, public_source, public_source_two_groups
):
    sp = client(super_admin_token)
    name = f"asteroid-{uuid.uuid4().hex}"
    super_obj_id = sp.post_super_obj(
        name=name,
        is_roid=True,
        obj_ids=[public_source.id, public_source_two_groups.id],
    ).id

    super_obj = sp.fetch_super_obj(super_obj_id)
    assert super_obj.name == name
    assert super_obj.is_roid is True
    assert {obj.id for obj in super_obj.objs} == {
        public_source.id,
        public_source_two_groups.id,
    }


def test_super_obj_filters(super_admin_token, public_source):
    sp = client(super_admin_token)
    name = f"asteroid-{uuid.uuid4().hex}"
    super_obj_id = sp.post_super_obj(
        name=name, is_roid=True, obj_ids=[public_source.id]
    ).id

    assert [s.id for s in sp.fetch_super_objs(name=name)] == [super_obj_id]

    assert super_obj_id in [s.id for s in sp.fetch_super_objs(obj_id=public_source.id)]

    assert sp.fetch_super_objs(name=name, is_roid=False) == []


def test_super_obj_membership_updates(
    super_admin_token, public_source, public_source_two_groups
):
    sp = client(super_admin_token)
    super_obj_id = sp.post_super_obj(
        name=f"asteroid-{uuid.uuid4().hex}", obj_ids=[public_source.id]
    ).id

    sp.update_super_obj(super_obj_id, add_obj_ids=[public_source_two_groups.id])

    super_obj = sp.fetch_super_obj(super_obj_id)
    assert {obj.id for obj in super_obj.objs} == {
        public_source.id,
        public_source_two_groups.id,
    }

    # adding the same Obj again must not duplicate it
    sp.update_super_obj(super_obj_id, add_obj_ids=[public_source_two_groups.id])

    assert len(sp.fetch_super_obj(super_obj_id).objs) == 2

    sp.update_super_obj(super_obj_id, remove_obj_ids=[public_source.id])

    assert [obj.id for obj in sp.fetch_super_obj(super_obj_id).objs] == [
        public_source_two_groups.id
    ]


def test_super_obj_rejects_conflicting_membership_args(
    super_admin_token, public_source
):
    sp = client(super_admin_token)
    super_obj_id = sp.post_super_obj(name=f"asteroid-{uuid.uuid4().hex}").id

    with pytest.raises(SkyPortalError) as err:
        sp.update_super_obj(
            super_obj_id,
            obj_ids=[public_source.id],
            add_obj_ids=[public_source.id],
        )
    assert err.value.status_code == 400


def test_super_obj_rejects_unknown_obj(super_admin_token):
    with pytest.raises(SkyPortalError) as err:
        client(super_admin_token).post_super_obj(
            name=f"asteroid-{uuid.uuid4().hex}", obj_ids=["does-not-exist"]
        )
    assert err.value.status_code == 400


def test_super_obj_delete_leaves_objs(super_admin_token, public_source):
    """Deleting a SuperObj must not delete the Objs it links."""
    sp = client(super_admin_token)
    super_obj_id = sp.post_super_obj(
        name=f"asteroid-{uuid.uuid4().hex}", obj_ids=[public_source.id]
    ).id

    sp.delete_super_obj(super_obj_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_super_obj(super_obj_id)
    assert err.value.status_code == 400

    assert sp.fetch_source(public_source.id).id == public_source.id


def test_super_obj_delete_requires_admin(
    super_admin_token, upload_data_token, public_source
):
    super_obj_id = (
        client(upload_data_token)
        .post_super_obj(name=f"asteroid-{uuid.uuid4().hex}", obj_ids=[public_source.id])
        .id
    )

    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token).delete_super_obj(super_obj_id)
    assert err.value.status_code == 401

    client(super_admin_token).delete_super_obj(super_obj_id)
