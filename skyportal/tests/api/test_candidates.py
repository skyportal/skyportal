import numpy.testing as npt
import uuid
from skyportal.tests import api


def test_candidate_list(view_only_token, public_candidate):
    status, data = api('GET', 'candidates', token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'


def test_token_user_retrieving_candidate(view_only_token, public_candidate):
    status, data = api('GET', f'candidates/{public_candidate.id}',
                       token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'
    assert all(k in data['data']['candidates'] for k in ['ra', 'dec', 'redshift',
                                                         'comments', 'thumbnails'])


def test_token_user_update_candidate(manage_sources_token, public_candidate):
    status, data = api('PATCH', f'candidates/{public_candidate.id}',
                       data={'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3},
                       token=manage_sources_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'candidates/{public_candidate.id}',
                       token=manage_sources_token)
    assert status == 200
    assert data['status'] == 'success'
    npt.assert_almost_equal(data['data']['candidates']['ra'], 234.22)
    npt.assert_almost_equal(data['data']['candidates']['redshift'], 3.0)


def test_cannot_update_candidate_without_permission(view_only_token, public_candidate):
    status, data = api('PATCH', f'candidates/{public_candidate.id}',
                       data={'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3},
                       token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_post_new_candidate(upload_data_token, view_only_token, public_group):
    candidate_id = str(uuid.uuid4())
    status, data = api('POST', 'candidates',
                       data={'id': candidate_id,
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3,
                             'group_ids': [public_group.id]},
                       token=upload_data_token)
    assert status == 200
    assert data['data']['id'] == candidate_id

    status, data = api('GET', f'candidates/{candidate_id}',
                       token=view_only_token)
    assert status == 200
    assert data['data']['candidates']['id'] == candidate_id
    npt.assert_almost_equal(data['data']['candidates']['ra'], 234.22)


def test_add_candidate_without_group_id(upload_data_token, view_only_token,
                                        public_group):
    candidate_id = str(uuid.uuid4())
    status, data = api('POST', 'candidates',
                       data={'id': candidate_id,
                             'ra': 234.22,
                             'dec': -22.33,
                             'redshift': 3,
                             'transient': False,
                             'ra_dis': 2.3},
                       token=upload_data_token)
    assert status == 200
    status, data = api('GET', f'candidates/{candidate_id}',
                       token=view_only_token)
    assert status == 200
    assert data['data']['candidates']['id'] == candidate_id
    npt.assert_almost_equal(data['data']['candidates']['ra'], 234.22)


def test_delete_candidate_cascade_photometry(manage_sources_token, public_candidate):
    photometry_ids = [phot.id for phot in public_candidate.photometry]
    assert len(photometry_ids) > 0
    for photometry_id in photometry_ids:
        status, data = api(
            'GET',
            f'photometry/{photometry_id}',
            token=manage_sources_token)
        assert status == 200

    status, data = api('DELETE', f'candidates/{public_candidate.id}',
                       token=manage_sources_token)
    assert status == 200

    status, data = api('GET', f'candidates/{public_candidate.id}',
                       token=manage_sources_token)
    assert status == 400

    for photometry_id in photometry_ids:
        status, data = api(
            'GET',
            f'photometry/{photometry_id}',
            token=manage_sources_token)
        assert status == 400


def test_delete_candidate_cascade_spectra(manage_sources_token, public_candidate):
    spec_ids = [spec.id for spec in public_candidate.spectra]
    assert len(spec_ids) > 0
    for spec_id in spec_ids:
        status, data = api(
            'GET',
            f'spectrum/{spec_id}',
            token=manage_sources_token)
        assert status == 200

    status, data = api('DELETE', f'candidates/{public_candidate.id}',
                       token=manage_sources_token)
    assert status == 200

    status, data = api('GET', f'candidates/{public_candidate.id}',
                       token=manage_sources_token)
    assert status == 400

    for spec_id in spec_ids:
        status, data = api(
            'GET',
            f'spectrum/{spec_id}',
            token=manage_sources_token)
        assert status == 400


def test_delete_candidate_cascade_comments(manage_sources_token, public_candidate):
    comment_ids = [comment.id for comment in public_candidate.comments]
    assert len(comment_ids) > 0
    for comment_id in comment_ids:
        status, data = api(
            'GET',
            f'comment/{comment_id}',
            token=manage_sources_token)
        assert status == 200

    status, data = api('DELETE', f'candidates/{public_candidate.id}',
                       token=manage_sources_token)
    assert status == 200

    status, data = api('GET', f'candidates/{public_candidate.id}',
                       token=manage_sources_token)
    assert status == 400

    for comment_id in comment_ids:
        status, data = api(
            'GET',
            f'comment/{comment_id}',
            token=manage_sources_token)
        assert status == 400


def test_delete_candidate_cascade_groupcandidate(upload_data_token,
                                                 manage_sources_token, public_group):
    candidate_id = str(uuid.uuid4())
    assert len(public_group.candidates) == 0

    status, data = api('POST', 'candidates',
                       data={'id': candidate_id,
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
    assert len(data['data']['group']['candidates']) == 1

    status, data = api('DELETE', f'candidates/{candidate_id}',
                       token=manage_sources_token)
    assert status == 200
    status, data = api('GET', f'candidates/{candidate_id}',
                       token=manage_sources_token)
    assert status == 400

    status, data = api('GET', f'groups/{public_group.id}',
                       token=manage_sources_token)
    assert len(data['data']['group']['candidates']) == 0
