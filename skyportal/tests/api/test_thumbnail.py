import os
import uuid
import datetime
import base64
from skyportal.tests import api
from skyportal.models import Thumbnail, DBSession, Photometry, Source


def test_token_user_post_get_thumbnail(upload_data_token, public_group):
    source_id = str(uuid.uuid4())
    status, data = api('POST', 'sources',
                       data={'id': source_id,
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3,
                             'group_ids': [public_group.id]},
                       token=upload_data_token)
    assert status == 200
    assert data['data']['id'] == source_id
    status, data = api('POST', 'photometry',
                       data={'source_id': source_id,
                             'time': str(datetime.datetime.now()),
                             'time_format': 'iso',
                             'time_scale': 'utc',
                             'instrument_id': 1,
                             'mag': 12.24,
                             'e_mag': 0.031,
                             'lim_mag': 14.1,
                             'filter': 'V'
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    orig_source_thumbnail_count = len(DBSession.query(Source).filter(
        Source.id == source_id).first().thumbnails)
    data = base64.b64encode(open(os.path.abspath('skyportal/tests/data/14gqr_new.png'),
                                 'rb').read())
    ttype = 'new'
    status, data = api('POST', 'thumbnail',
                       data={'source_id': source_id,
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
    assert data['data']['thumbnail']['type'] == 'new'

    assert (DBSession.query(Thumbnail).filter(Thumbnail.id == thumbnail_id)
            .first().source.id) == source_id
    assert len(DBSession.query(Source).filter(Source.id == source_id).first()
               .thumbnails) == orig_source_thumbnail_count + 1


def test_token_user_delete_thumbnail_cascade_source(upload_data_token,
                                                    manage_sources_token,
                                                    public_group):
    source_id = str(uuid.uuid4())
    status, data = api('POST', 'sources',
                       data={'id': source_id,
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3,
                             'group_ids': [public_group.id]},
                       token=upload_data_token)
    assert status == 200
    assert data['data']['id'] == source_id
    status, data = api('POST', 'photometry',
                       data={'source_id': source_id,
                             'time': str(datetime.datetime.now()),
                             'time_format': 'iso',
                             'time_scale': 'utc',
                             'instrument_id': 1,
                             'mag': 12.24,
                             'e_mag': 0.031,
                             'lim_mag': 14.1,
                             'filter': 'V'
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    orig_source_thumbnail_count = len(DBSession.query(Source).filter(
        Source.id == source_id).first().thumbnails)
    data = base64.b64encode(open(os.path.abspath('skyportal/tests/data/14gqr_new.png'),
                                 'rb').read())
    ttype = 'new'
    status, data = api('POST', 'thumbnail',
                       data={'source_id': source_id,
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
    assert data['data']['thumbnail']['type'] == 'new'

    assert (DBSession.query(Thumbnail).filter(Thumbnail.id == thumbnail_id)
            .first().source.id) == source_id
    assert len(DBSession.query(Source).filter(Source.id == source_id).first()
          .thumbnails) == orig_source_thumbnail_count + 1

    status, data = api(
        'DELETE',
        f'thumbnail/{thumbnail_id}',
        token=manage_sources_token)
    assert status == 200
    assert data['status'] == 'success'

    assert len(DBSession.query(Source).filter(Source.id == source_id).first()
          .thumbnails) == orig_source_thumbnail_count


def test_token_user_post_get_thumbnail_phot_id(upload_data_token, public_group):
    source_id = str(uuid.uuid4())
    status, data = api('POST', 'sources',
                       data={'id': source_id,
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3,
                             'group_ids': [public_group.id]},
                       token=upload_data_token)
    assert status == 200
    assert data['data']['id'] == source_id
    status, data = api('POST', 'photometry',
                       data={'source_id': source_id,
                             'time': str(datetime.datetime.now()),
                             'time_format': 'iso',
                             'time_scale': 'utc',
                             'instrument_id': 1,
                             'mag': 12.24,
                             'e_mag': 0.031,
                             'lim_mag': 14.1,
                             'filter': 'V'
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    photometry_id = data['data']['ids'][0]

    orig_source_thumbnail_count = len(DBSession.query(Source).filter(
        Source.id == source_id).first().thumbnails)
    data = base64.b64encode(open(os.path.abspath('skyportal/tests/data/14gqr_new.png'),
                                 'rb').read())
    ttype = 'new'
    status, data = api('POST', 'thumbnail',
                       data={'photometry_id': photometry_id,
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
    assert data['data']['thumbnail']['type'] == 'new'

    assert (DBSession.query(Thumbnail).filter(Thumbnail.id == thumbnail_id)
            .first().source.id) == source_id
    assert len(DBSession.query(Source).filter(Source.id == source_id).first()
               .thumbnails) == orig_source_thumbnail_count + 1


def test_cannot_post_thumbnail_invalid_ttype(upload_data_token, public_group):
    source_id = str(uuid.uuid4())
    status, data = api('POST', 'sources',
                       data={'id': source_id,
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3,
                             'group_ids': [public_group.id]},
                       token=upload_data_token)
    assert status == 200
    assert data['data']['id'] == source_id
    status, data = api('POST', 'photometry',
                       data={'source_id': source_id,
                             'time': str(datetime.datetime.now()),
                             'time_format': 'iso',
                             'time_scale': 'utc',
                             'instrument_id': 1,
                             'mag': 12.24,
                             'e_mag': 0.031,
                             'lim_mag': 14.1,
                             'filter': 'V'
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    data = base64.b64encode(open(os.path.abspath('skyportal/tests/data/14gqr_new.png'),
                                 'rb').read())
    ttype = 'invalid_ttype'
    status, data = api('POST', 'thumbnail',
                       data={'source_id': source_id,
                             'data': data,
                             'ttype': ttype
                       },
                       token=upload_data_token)
    assert status == 400
    assert data['status'] == 'error'
    assert 'is not among the defined enum values' in data['message']


def test_cannot_post_thumbnail_invalid_image_type(upload_data_token, public_group):
    source_id = str(uuid.uuid4())
    status, data = api('POST', 'sources',
                       data={'id': source_id,
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3,
                             'group_ids': [public_group.id]},
                       token=upload_data_token)
    assert status == 200
    assert data['data']['id'] == source_id
    status, data = api('POST', 'photometry',
                       data={'source_id': source_id,
                             'time': str(datetime.datetime.now()),
                             'time_format': 'iso',
                             'time_scale': 'utc',
                             'instrument_id': 1,
                             'mag': 12.24,
                             'e_mag': 0.031,
                             'lim_mag': 14.1,
                             'filter': 'V'
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    data = base64.b64encode(open(os.path.abspath('skyportal/tests/data/candid-87704463155000_ref.jpg'),
                                 'rb').read())
    ttype = 'ref'
    status, data = api('POST', 'thumbnail',
                       data={'source_id': source_id,
                             'data': data,
                             'ttype': ttype
                       },
                       token=upload_data_token)
    assert status == 400
    assert data['status'] == 'error'
    assert 'Invalid thumbnail image type. Only PNG are supported.' in data['message']


def test_cannot_post_thumbnail_invalid_size(upload_data_token, public_group):
    source_id = str(uuid.uuid4())
    status, data = api('POST', 'sources',
                       data={'id': source_id,
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3,
                             'group_ids': [public_group.id]},
                       token=upload_data_token)
    assert status == 200
    assert data['data']['id'] == source_id
    status, data = api('POST', 'photometry',
                       data={'source_id': source_id,
                             'time': str(datetime.datetime.now()),
                             'time_format': 'iso',
                             'time_scale': 'utc',
                             'instrument_id': 1,
                             'mag': 12.24,
                             'e_mag': 0.031,
                             'lim_mag': 14.1,
                             'filter': 'V'
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    data = base64.b64encode(open(os.path.abspath('skyportal/tests/data/14gqr_new_50px.png'),
                                 'rb').read())
    ttype = 'ref'
    status, data = api('POST', 'thumbnail',
                       data={'source_id': source_id,
                             'data': data,
                             'ttype': ttype
                       },
                       token=upload_data_token)
    assert status == 400
    assert data['status'] == 'error'
    assert 'Invalid thumbnail size.' in data['message']



def test_cannot_post_thumbnail_invalid_file_type(upload_data_token, public_group):
    source_id = str(uuid.uuid4())
    status, data = api('POST', 'sources',
                       data={'id': source_id,
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3,
                             'group_ids': [public_group.id]},
                       token=upload_data_token)
    assert status == 200
    assert data['data']['id'] == source_id
    status, data = api('POST', 'photometry',
                       data={'source_id': source_id,
                             'time': str(datetime.datetime.now()),
                             'time_format': 'iso',
                             'time_scale': 'utc',
                             'instrument_id': 1,
                             'mag': 12.24,
                             'e_mag': 0.031,
                             'lim_mag': 14.1,
                             'filter': 'V'
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    data = base64.b64encode(open(os.path.abspath('skyportal/tests/data/phot.csv'),
                                 'rb').read())
    ttype = 'ref'
    status, data = api('POST', 'thumbnail',
                       data={'source_id': source_id,
                             'data': data,
                             'ttype': ttype
                       },
                       token=upload_data_token)
    assert status == 400
    assert data['status'] == 'error'
    assert 'cannot identify image file' in data['message']
