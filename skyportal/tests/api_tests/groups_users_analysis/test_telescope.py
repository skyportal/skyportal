import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.telescopes import TelescopePost, TelescopePut

from skyportal.tests import client


def test_get_telescope_longitude_longitude_box(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    telescope_id_1 = sp.post_telescope(
        TelescopePost(
            name=name,
            nickname=name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
            skycam_link="http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg",
            robotic=True,
        )
    ).id

    name = str(uuid.uuid4())
    telescope_id_2 = sp.post_telescope(
        TelescopePost(
            name=name,
            nickname=name,
            lat=-30.0,
            lon=60.0,
            elevation=0.0,
            diameter=10.0,
            skycam_link="http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg",
            robotic=True,
        )
    ).id

    in_box = sp.fetch_telescopes(
        latitude_min=-45.0,
        latitude_max=-15.0,
        longitude_min=45.0,
        longitude_max=75.0,
    )
    assert telescope_id_2 in [tel.id for tel in in_box]
    assert telescope_id_1 not in [tel.id for tel in in_box]


def test_token_user_post_get_telescope(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    post_data = TelescopePost(
        name=name,
        nickname=name,
        lat=0.0,
        lon=0.0,
        elevation=0.0,
        diameter=10.0,
        skycam_link="http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg",
        robotic=True,
    )

    telescope_id = sp.post_telescope(post_data).id
    fetched = sp.fetch_telescope(telescope_id)
    for key, value in post_data.model_dump(exclude_none=True).items():
        assert getattr(fetched, key) == value


def test_fetch_telescope_by_name(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    post_data = TelescopePost(
        name=name,
        nickname=name,
        lat=0.0,
        lon=0.0,
        elevation=0.0,
        diameter=10.0,
        skycam_link="http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg",
    )

    sp.post_telescope(post_data)

    matches = sp.fetch_telescopes(name=name)
    assert len(matches) == 1
    for key, value in post_data.model_dump(exclude_none=True).items():
        assert getattr(matches[0], key) == value


def test_token_user_update_telescope(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=name,
            nickname=name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
            robotic=True,
        )
    ).id
    assert sp.fetch_telescope(telescope_id).diameter == 10.0

    sp.update_telescope(
        telescope_id,
        TelescopePut(
            name=name,
            nickname=name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=12.0,
        ),
    )
    assert sp.fetch_telescope(telescope_id).diameter == 12.0


def test_token_user_delete_telescope(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=name,
            nickname=name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
            robotic=False,
        )
    ).id
    assert sp.fetch_telescope(telescope_id).diameter == 10.0

    sp.delete_telescope(telescope_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_telescope(telescope_id)
    assert err.value.status_code == 400
