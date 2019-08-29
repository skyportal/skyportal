import numpy.testing as npt
from skyportal.tests import api


def test_source_list(view_only_token):
    status, data = api('GET', 'sources', token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'


def test_token_user_retrieving_source(view_only_token, public_source):
    status, data = api('GET', f'sources/{public_source.id}',
                       token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'
    assert all(k in data['data']['sources'] for k in ['ra', 'dec', 'redshift',
                                                      'created', 'id'])


def test_token_user_update_source(manage_sources_token, public_source):
    status, data = api('PUT', f'sources/{public_source.id}',
                       data={'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3},
                       token=manage_sources_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'sources/{public_source.id}',
                       token=manage_sources_token)
    assert status == 200
    assert data['status'] == 'success'
    npt.assert_almost_equal(data['data']['sources']['ra'], 234.22)
    npt.assert_almost_equal(data['data']['sources']['redshift'], 3.0)


def test_cannot_update_source_without_permission(view_only_token, public_source):
    status, data = api('PUT', f'sources/{public_source.id}',
                       data={'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3},
                       token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_post_new_source(upload_data_token, view_only_token, public_group):
    status, data = api('POST', 'sources',
                       data={'id': 'testID',
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3,
                             'group_ids': [public_group.id]},
                       token=upload_data_token)
    assert status == 200
    assert data['data']['id'] == 'testID'

    status, data = api('GET', 'sources/testID',
                       token=view_only_token)
    assert status == 200
    assert data['data']['sources']['id'] == 'testID'
    npt.assert_almost_equal(data['data']['sources']['ra'], 234.22)


def test_add_source_without_group_id(upload_data_token, view_only_token,
                                     public_group):
    status, data = api('POST', 'sources',
                       data={'id': 'testID2',
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3},
                       token=upload_data_token)
    assert status == 200
    status, data = api('GET', 'sources/testID2',
                       token=view_only_token)
    assert status == 200
    assert data['data']['sources']['id'] == 'testID2'
    npt.assert_almost_equal(data['data']['sources']['ra'], 234.22)
