import numpy.testing as npt
import uuid
from skyportal.tests import api
from skyportal.models import DBSession, Group


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
                                                      'created_at', 'id'])


def test_token_user_retrieving_source_photometry(view_only_token, public_source):
    status, data = api('GET', f'sources/{public_source.id}/photometry',
                       token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'
    assert isinstance(data['data']['photometry'], list)
    assert 'mjd' in data['data']['photometry'][0]


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

    status, data = api('GET', f'sources/{source_id}',
                       token=view_only_token)
    assert status == 200
    assert data['data']['sources']['id'] == source_id
    npt.assert_almost_equal(data['data']['sources']['ra'], 234.22)


def test_add_source_without_group_id(upload_data_token, view_only_token,
                                     public_group):
    source_id = str(uuid.uuid4())
    status, data = api('POST', 'sources',
                       data={'id': source_id,
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3},
                       token=upload_data_token)
    assert status == 200
    status, data = api('GET', f'sources/{source_id}',
                       token=view_only_token)
    assert status == 200
    assert data['data']['sources']['id'] == source_id
    npt.assert_almost_equal(data['data']['sources']['ra'], 234.22)


def test_delete_source_cascade_photometry(manage_sources_token, public_source):
    photometry_ids = [phot.id for phot in public_source.photometry]
    assert len(photometry_ids) > 0
    for photometry_id in photometry_ids:
        status, data = api(
            'GET',
            f'photometry/{photometry_id}',
            token=manage_sources_token)
        assert status == 200

    status, data = api('DELETE', f'sources/{public_source.id}',
                       token=manage_sources_token)
    assert status == 200

    status, data = api('GET', f'sources/{public_source.id}',
                       token=manage_sources_token)
    assert status == 400

    for photometry_id in photometry_ids:
        status, data = api(
            'GET',
            f'photometry/{photometry_id}',
            token=manage_sources_token)
        assert status == 400


def test_delete_source_cascade_spectra(manage_sources_token, public_source):
    spec_ids = [spec.id for spec in public_source.spectra]
    assert len(spec_ids) > 0
    for spec_id in spec_ids:
        status, data = api(
            'GET',
            f'spectrum/{spec_id}',
            token=manage_sources_token)
        assert status == 200

    status, data = api('DELETE', f'sources/{public_source.id}',
                       token=manage_sources_token)
    assert status == 200

    status, data = api('GET', f'sources/{public_source.id}',
                       token=manage_sources_token)
    assert status == 400

    for spec_id in spec_ids:
        status, data = api(
            'GET',
            f'spectrum/{spec_id}',
            token=manage_sources_token)
        assert status == 400


def test_delete_source_cascade_comments(manage_sources_token, public_source):
    comment_ids = [comment.id for comment in public_source.comments]
    assert len(comment_ids) > 0
    for comment_id in comment_ids:
        status, data = api(
            'GET',
            f'comment/{comment_id}',
            token=manage_sources_token)
        assert status == 200

    status, data = api('DELETE', f'sources/{public_source.id}',
                       token=manage_sources_token)
    assert status == 200

    status, data = api('GET', f'sources/{public_source.id}',
                       token=manage_sources_token)
    assert status == 400

    for comment_id in comment_ids:
        status, data = api(
            'GET',
            f'comment/{comment_id}',
            token=manage_sources_token)
        assert status == 400


def test_delete_source_cascade_groupsource(upload_data_token,
                                           manage_sources_token, public_group):
    source_id = str(uuid.uuid4())
    print(public_group.id)
    assert len(public_group.sources) == 0

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

    status, data = api('GET', f'groups/{public_group.id}',
                       token=manage_sources_token)
    assert len(data['data']['group']['sources']) == 1

    status, data = api('DELETE', f'sources/{source_id}',
                       token=manage_sources_token)
    assert status == 200
    status, data = api('GET', f'sources/{source_id}',
                       token=manage_sources_token)
    assert status == 400

    status, data = api('GET', f'groups/{public_group.id}',
                       token=manage_sources_token)
    assert len(data['data']['group']['sources']) == 0
