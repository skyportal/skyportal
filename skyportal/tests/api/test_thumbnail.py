import os
import uuid
import base64
from skyportal.tests import api
from skyportal.models import DBSession, Obj, Thumbnail


def test_token_user_post_get_thumbnail(upload_data_token, public_group, ztf_camera):

    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    orig_source_thumbnail_count = len(
        DBSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails
    )
    data = base64.b64encode(
        open(os.path.abspath('skyportal/tests/data/14gqr_new.png'), 'rb').read()
    )
    ttype = 'new'
    status, data = api(
        'POST',
        'thumbnail',
        data={'obj_id': obj_id, 'data': data, 'ttype': ttype},
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    thumbnail_id = data['data']['id']
    assert isinstance(thumbnail_id, int)

    status, data = api('GET', f'thumbnail/{thumbnail_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['type'] == 'new'

    assert (
        DBSession.query(Thumbnail).filter(Thumbnail.id == thumbnail_id).first().obj.id
    ) == obj_id
    assert (
        len(DBSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails)
        == orig_source_thumbnail_count + 1
    )


def test_cannot_post_thumbnail_invalid_ttype(
    upload_data_token, public_group, ztf_camera
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    data = base64.b64encode(
        open(os.path.abspath('skyportal/tests/data/14gqr_new.png'), 'rb').read()
    )
    ttype = 'invalid_ttype'
    status, data = api(
        'POST',
        'thumbnail',
        data={'obj_id': obj_id, 'data': data, 'ttype': ttype},
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'
    assert 'is not among the defined enum values' in data['message']


def test_cannot_post_thumbnail_invalid_image_type(
    upload_data_token, public_group, ztf_camera
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    data = base64.b64encode(
        open(
            os.path.abspath('skyportal/tests/data/candid-87704463155000_ref.jpg'), 'rb'
        ).read()
    )
    ttype = 'ref'
    status, data = api(
        'POST',
        'thumbnail',
        data={'obj_id': obj_id, 'data': data, 'ttype': ttype},
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'
    assert 'Invalid thumbnail image type. Only PNG are supported.' in data['message']


def test_cannot_post_thumbnail_invalid_size(
    upload_data_token, public_group, ztf_camera
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    data = base64.b64encode(
        open(os.path.abspath('skyportal/tests/data/14gqr_new_13px.png'), 'rb').read()
    )
    ttype = 'ref'
    status, data = api(
        'POST',
        'thumbnail',
        data={'obj_id': obj_id, 'data': data, 'ttype': ttype},
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'
    assert 'Invalid thumbnail size.' in data['message']


def test_cannot_post_thumbnail_invalid_file_type(
    upload_data_token, public_group, ztf_camera
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    data = base64.b64encode(os.urandom(2048))  # invalid image data
    ttype = 'ref'
    status, data = api(
        'POST',
        'thumbnail',
        data={'obj_id': obj_id, 'data': data, 'ttype': ttype},
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'
    assert 'cannot identify image file' in data['message']


def test_delete_thumbnail_deletes_file_on_disk(
    upload_data_token, super_admin_token, public_group
):

    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    thumbnail_data = base64.b64encode(
        open(os.path.abspath('skyportal/tests/data/14gqr_new.png'), 'rb').read()
    )
    ttype = 'new'
    status, data = api(
        'POST',
        'thumbnail',
        data={'obj_id': obj_id, 'data': thumbnail_data, 'ttype': ttype},
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    thumbnail_id = data['data']['id']
    assert isinstance(thumbnail_id, int)

    status, data = api('GET', f'thumbnail/{thumbnail_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['type'] == ttype

    thumbnail = DBSession.query(Thumbnail).filter(Thumbnail.id == thumbnail_id).first()
    assert thumbnail.obj_id == obj_id
    fpath = thumbnail.file_uri
    assert os.path.exists(fpath)

    status, data = api('DELETE', f'thumbnail/{thumbnail_id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    assert not os.path.exists(fpath)


def test_delete_obj_deletes_thumbnail_file_on_disk(
    upload_data_token, super_admin_token, public_group
):

    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    thumbnail_data = base64.b64encode(
        open(os.path.abspath('skyportal/tests/data/14gqr_new.png'), 'rb').read()
    )
    ttype = 'new'
    status, data = api(
        'POST',
        'thumbnail',
        data={'obj_id': obj_id, 'data': thumbnail_data, 'ttype': ttype},
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    thumbnail_id = data['data']['id']
    assert isinstance(thumbnail_id, int)

    status, data = api('GET', f'thumbnail/{thumbnail_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['type'] == ttype

    thumbnail = DBSession.query(Thumbnail).filter(Thumbnail.id == thumbnail_id).first()
    assert thumbnail.obj_id == obj_id
    fpath = thumbnail.file_uri
    assert os.path.exists(fpath)

    status, data = api('DELETE', f'objs/{obj_id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    assert not os.path.exists(fpath)
