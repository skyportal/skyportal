import pytest
import numpy.testing as npt
import uuid
from skyportal.tests import api
from skyportal.models import DBSession, Source


def test_source_list(view_only_token):
    status, data = api('GET', 'sources', token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'


def test_token_user_retrieving_source(view_only_token, public_source):
    status, data = api('GET', f'sources/{public_source.id}', token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'
    assert all(k in data['data'] for k in ['ra', 'dec', 'redshift', 'created_at', 'id'])


def test_token_user_update_source(manage_sources_token, public_source):
    status, data = api(
        'PUT',
        f'sources/{public_source.id}',
        data={
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
        },
        token=manage_sources_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'sources/{public_source.id}', token=manage_sources_token)
    assert status == 200
    assert data['status'] == 'success'
    npt.assert_almost_equal(data['data']['ra'], 234.22)
    npt.assert_almost_equal(data['data']['redshift'], 3.0)


def test_cannot_update_source_without_permission(view_only_token, public_source):
    status, data = api(
        'PUT',
        f'sources/{public_source.id}',
        data={
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
        },
        token=view_only_token,
    )
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_post_new_source(upload_data_token, view_only_token, public_group):
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

    status, data = api('GET', f'sources/{obj_id}', token=view_only_token)
    assert status == 200
    assert data['data']['id'] == obj_id
    npt.assert_almost_equal(data['data']['ra'], 234.22)


def test_add_source_without_group_id(upload_data_token, view_only_token, public_group):
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
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api('GET', f'sources/{obj_id}', token=view_only_token)
    assert status == 200
    assert data['data']['id'] == obj_id
    npt.assert_almost_equal(data['data']['ra'], 234.22)


def test_starlist(manage_sources_token, public_source):
    status, data = api(
        'PUT',
        f'sources/{public_source.id}',
        data={'ra': 234.22, 'dec': -22.33},
        token=manage_sources_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET',
        f'sources/{public_source.id}/offsets?facility=P200&how_many=1',
        token=manage_sources_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']["noffsets"] == 1
    assert data['data']['queries_issued'] == 1
    assert data['data']["facility"] == 'P200'
    assert 'starlist_str' in data['data']
    assert isinstance(data['data']["starlist_info"][0]["ra"], float)

    status, data = api(
        'GET', f'sources/{public_source.id}/offsets', token=manage_sources_token
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']["noffsets"] == 3
    assert data['data']["facility"] == 'Keck'
    assert 'starlist_str' in data['data']
    assert isinstance(data['data']["starlist_info"][2]["dec"], float)


@pytest.mark.xfail(strict=False)
def test_finder(manage_sources_token, public_source):
    status, data = api(
        'PUT',
        f'sources/{public_source.id}',
        data={'ra': 234.22, 'dec': -22.33},
        token=manage_sources_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    response = api(
        'GET',
        f'sources/{public_source.id}/finder?imsize=2',
        token=manage_sources_token,
        raw_response=True,
    )
    status = response.status_code
    data = response.text
    assert status == 200
    assert isinstance(data, str)
    assert data[0:10].find("PDF") != -1
    assert response.headers.get("Content-Type", "Empty").find("application/pdf") != -1

    # try an image source we dont know about
    status, data = api(
        'GET',
        f'sources/{public_source.id}/finder?image_source=whoknows',
        token=manage_sources_token,
    )
    assert status == 400

    # try an image too big
    status, data = api(
        'GET',
        f'sources/{public_source.id}/finder?imsize=30',
        token=manage_sources_token,
    )
    assert status == 400
