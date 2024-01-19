import os
import uuid
import base64
from skyportal.tests import api
from skyportal.models import ThreadSession, Obj, Thumbnail


def test_token_user_delete_thumbnail_cascade_source(
    upload_data_token, super_admin_token, public_group, ztf_camera
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

    orig_source_thumbnail_count = len(
        ThreadSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails
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
        ThreadSession.query(Thumbnail)
        .filter(Thumbnail.id == thumbnail_id)
        .first()
        .obj.id
    ) == obj_id
    assert (
        len(ThreadSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails)
        == orig_source_thumbnail_count + 1
    )

    status, data = api('DELETE', f'thumbnail/{thumbnail_id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    assert (
        len(ThreadSession.query(Obj).filter(Obj.id == obj_id).first().thumbnails)
        == orig_source_thumbnail_count
    )
