import datetime

from skyportal.tests import api


def test_token_user_post_get_photometry_data(upload_data_token, public_source):
    status, data = api('POST', 'photometry',
                       data={'source_id': str(public_source.id),
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
    status, data = api(
        'GET',
        f'photometry/{photometry_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['photometry']['mag'] == 12.24



def test_token_user_post_photometry_data_series(upload_data_token, public_source):
    status, data = api(
        'POST',
        'photometry',
        data={'source_id': str(public_source.id),
              'time': [str(datetime.datetime.now()),
                          str(datetime.datetime.now() + datetime.timedelta(days=1)),
                          str(datetime.datetime.now() + datetime.timedelta(days=2))],
              'time_format': 'iso',
              'time_scale': 'utc',
              'instrument_id': 1,
              'mag': [12.24, 12.52, 12.70],
              'e_mag': [0.031, 0.029, 0.030],
              'lim_mag': 14.1,
              'filter': 'V'},
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
    assert data['data']['photometry']['mag'] == 12.52


def test_post_photometry_no_access_token(view_only_token, public_source):
    status, data = api('POST', 'photometry',
                       data={'source_id': str(public_source.id),
                             'time': str(datetime.datetime.now()),
                             'time_format': 'iso',
                             'time_scale': 'utc',
                             'instrument_id': 1,
                             'mag': 12.24,
                             'e_mag': 0.031,
                             'lim_mag': 14.1,
                             'filter': 'V'
                       },
                       token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_update_photometry(upload_data_token,
                                      manage_sources_token,
                                      public_source):
    status, data = api('POST', 'photometry',
                       data={'source_id': str(public_source.id),
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
    status, data = api(
        'GET',
        f'photometry/{photometry_id}',
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['photometry']['mag'] == 12.24

    status, data = api(
        'PUT',
        f'photometry/{photometry_id}',
        data={'mag': 11.0},
        token=manage_sources_token)
    status, data = api(
        'GET',
        f'photometry/{photometry_id}',
        token=upload_data_token)
    assert data['data']['photometry']['mag'] == 11.0
