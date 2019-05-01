import datetime

from skyportal.tests import api


def test_token_user_post_photometry_data(upload_data_token, public_source):
    status, data = api('POST', 'photometry',
                       data={'sourceID': str(public_source.id),
                             'obsTime': str(datetime.datetime.now()),
                             'timeFormat': 'iso',
                             'timeScale': 'utc',
                             'instrumentID': 1,
                             'mag': 12.24,
                             'e_mag': 0.031,
                             'lim_mag': 14.1,
                             'filter': 'V'
                       },
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'


def test_token_user_post_photometry_data_series(upload_data_token, public_source):
    status, data = api(
        'POST',
        'photometry',
        data={'sourceID': str(public_source.id),
              'obsTime': [str(datetime.datetime.now()),
                          str(datetime.datetime.now() + datetime.timedelta(days=1)),
                          str(datetime.datetime.now() + datetime.timedelta(days=2))],
              'timeFormat': 'iso',
              'timeScale': 'utc',
              'instrumentID': 1,
              'mag': [12.24, 12.52, 12.70],
              'e_mag': [0.031, 0.029, 0.030],
              'lim_mag': 14.1,
              'filter': 'V'},
        token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'


def test_photometry_no_access_token(view_only_token, public_source):
    status, data = api('POST', 'photometry',
                       data={'sourceID': str(public_source.id),
                             'obsTime': str(datetime.datetime.now()),
                             'timeFormat': 'iso',
                             'timeScale': 'utc',
                             'instrumentID': 1,
                             'mag': 12.24,
                             'e_mag': 0.031,
                             'lim_mag': 14.1,
                             'filter': 'V'
                       },
                       token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'
