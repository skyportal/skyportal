import os
import datetime
import base64
from skyportal.tests import api
from skyportal.models import Thumbnail, DBSession, Photometry


def test_token_user_post_get_thumbnail(upload_data_token, public_source):
    data = base64.b64encode(open(os.path.abspath('skyportal/tests/data/14gqr_new.png'),
                                 'rb').read()),
    ttype = 'new'
    status, data = api('POST', 'thumbnail',
                       data={'source_id': str(public_source.id),
                             'data': data,
                             'ttype': ttype
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    thumbnail_id = data['data']['id']
    assert isinstance(thumbnail_id, int)

    status, data = api(
        'GET',
        f'thumbnail/{thumbnail_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['thumbnail']['ttype'] == new

    assert (DBSession.query(Thumbnail).filter(Thumbnail.id == thumbnail_id)
            .first().source.id) == public_source.id


def test_token_user_delete_thumbnail(upload_data_token, manage_sources_token,
                                     public_source):
    data = base64.b64encode(open(os.path.abspath('skyportal/tests/data/14gqr_new.png'),
                                 'rb').read()),
    ttype = 'new'
    status, data = api('POST', 'thumbnail',
                       data={'source_id': str(public_source.id),
                             'data': data,
                             'ttype': ttype
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    thumbnail_id = data['data']['id']
    assert isinstance(thumbnail_id, int)

    status, data = api(
        'GET',
        f'thumbnail/{thumbnail_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['thumbnail']['ttype'] == new

    assert (DBSession.query(Thumbnail).filter(Thumbnail.id == thumbnail_id)
            .first().source.id) == public_source.id
    assert len(DBSession.query(Source).filter(Source.id == public_source.id).first()
               .thumbnails) == 1

    status, data = api(
        'DELETE',
        f'thumbnail/{thumbnail_id}',
        token=manage_sources_token)
    assert status == 200
    assert data['status'] == 'success'

    assert len(DBSession.query(Source).filter(Source.id == public_source.id).first()
               .thumbnails) == 0
