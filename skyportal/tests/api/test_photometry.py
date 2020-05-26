import os
import datetime
import base64
from skyportal.tests import api
from skyportal.models import Thumbnail, DBSession, Photometry


def test_token_user_post_get_photometry_data(upload_data_token, public_source):
    status, data = api('POST', 'photometry',
                       data={'obj_id': str(public_source.id),
                             'mjd': 58000.,
                             'instrument_id': 1,
                             'flux': 12.24,
                             'fluxerr': 0.031,
                             'zp': 25.,
                             'zpsys': 'ab',
                             'filter': 'bessellv'
                             },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET',
        f'photometry/{photometry_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['flux'] == 12.24


def test_token_user_post_photometry_data_series(upload_data_token, public_source):
    status, data = api(
        'POST',
        'photometry',
        data={'obj_id': str(public_source.id),
              'mjd': [58000., 58001., 58002.],
              'instrument_id': 1,
              'flux': [12.24, 12.52, 12.70],
              'fluxerr': [0.031, 0.029, 0.030],
              'filter': ['bessellv', 'bessellv', 'bessellv'],
              'zp': [25., 25., 25.],
              'zpsys': ['ab', 'ab', 'ab']},
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][1]
    status, data = api(
        'GET',
        f'photometry/{photometry_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['flux'] == 12.52


def test_post_photometry_no_access_token(view_only_token, public_source):
    status, data = api('POST', 'photometry',
                       data={'obj_id': str(public_source.id),
                             'mjd': 58000.,
                             'instrument_id': 1,
                             'flux': 12.24,
                             'fluxerr': 0.031,
                             'zp': 25.,
                             'zpsys': 'ab',
                             'filter': 'bessellv'
                             },
                       token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_update_photometry(upload_data_token,
                                      manage_sources_token,
                                      public_source):
    status, data = api('POST', 'photometry',
                       data={'obj_id': str(public_source.id),
                             'mjd': 58000.,
                             'instrument_id': 1,
                             'flux': 12.24,
                             'fluxerr': 0.031,
                             'zp': 25.,
                             'zpsys': 'ab',
                             'filter': 'bessellv'
                             },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET',
        f'photometry/{photometry_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['flux'] == 12.24

    status, data = api(
        'PUT',
        f'photometry/{photometry_id}',
        data={'flux': 11.0},
        token=manage_sources_token)
    status, data = api(
        'GET',
        f'photometry/{photometry_id}',
        token=upload_data_token)
    assert data['data']['flux'] == 11.0


def test_delete_photometry_data(upload_data_token, manage_sources_token,
                                public_source):
    status, data = api('POST', 'photometry',
                       data={'obj_id': str(public_source.id),
                             'mjd': 58000.,
                             'instrument_id': 1,
                             'flux': 12.24,
                             'fluxerr': 0.031,
                             'zp': 25.,
                             'zpsys': 'ab',
                             'filter': 'bessellv'
                             },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET',
        f'photometry/{photometry_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['flux'] == 12.24

    status, data = api(
        'DELETE',
        f'photometry/{photometry_id}',
        token=manage_sources_token)
    assert status == 200

    status, data = api(
        'GET',
        f'photometry/{photometry_id}',
        token=upload_data_token)
    assert status == 400


def test_delete_photometry_cascades_to_thumbnail(manage_sources_token,
                                                 public_source):
    for phot in public_source.photometry:
        if len(phot.thumbnails) > 0:
            photometry_id = phot.id
            thumbnail_id = phot.thumbnails[0].id
            break
    assert DBSession.query(Thumbnail).filter(Thumbnail.id == int(thumbnail_id)).count() > 0

    status, data = api(
        'DELETE',
        f'photometry/{photometry_id}',
        token=manage_sources_token)
    assert status == 200

    assert DBSession.query(Thumbnail).filter(Thumbnail.id == int(thumbnail_id)).count() == 0


def test_token_user_post_photometry_thumbnail(upload_data_token, public_source):
    thumbnails = [
        {'data': base64.b64encode(open(os.path.abspath(f'skyportal/tests/data/14gqr_{suffix}.png'),
                                       'rb').read()),
         'ttype': suffix}
        for suffix in ['new', 'ref', 'sub']
    ]
    status, data = api('POST', 'photometry',
                       data={'obj_id': str(public_source.id),
                             'mjd': 58000.,
                             'instrument_id': 1,
                             'flux': 12.24,
                             'fluxerr': 0.031,
                             'zp': 25.,
                             'zpsys': 'ab',
                             'filter': 'bessellv',
                             'thumbnails': thumbnails
                             },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET',
        f'photometry/{photometry_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['flux'] == 12.24

    assert len(DBSession.query(Photometry).filter(Photometry.id == photometry_id)
               .first().thumbnails) == 3
