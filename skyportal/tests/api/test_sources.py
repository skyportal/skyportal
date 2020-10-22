import uuid
import pytest
import numpy.testing as npt
import numpy as np
from skyportal.tests import api
from skyportal.models import cosmo


def test_source_list(view_only_token):
    status, data = api('GET', 'sources', token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'


def test_source_existence(view_only_token, public_source):
    status = api('HEAD', f'sources/{public_source.id}', token=view_only_token)
    assert status == 200

    status = api('HEAD', f'sources/{public_source.id[:-1]}', token=view_only_token)
    assert status == 400


def test_token_user_retrieving_source(view_only_token, public_source):
    status, data = api('GET', f'sources/{public_source.id}', token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'
    assert all(
        k in data['data'] for k in ['ra', 'dec', 'redshift', 'dm', 'created_at', 'id']
    )
    assert "photometry" not in data['data']


def test_token_user_retrieving_source_with_phot(view_only_token, public_source):
    status, data = api(
        'GET',
        f'sources/{public_source.id}?includePhotometry=true',
        token=view_only_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert all(
        k in data['data']
        for k in ['ra', 'dec', 'redshift', 'dm', 'created_at', 'id', 'photometry']
    )


def test_token_user_update_source(upload_data_token, public_source):
    status, data = api(
        'PATCH',
        f'sources/{public_source.id}',
        data={
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'sources/{public_source.id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    npt.assert_almost_equal(data['data']['ra'], 234.22)
    npt.assert_almost_equal(data['data']['redshift'], 3.0)
    npt.assert_almost_equal(
        cosmo.luminosity_distance(3.0).value, data['data']['luminosity_distance']
    )


def test_distance_modulus(upload_data_token, public_source):
    status, data = api(
        'PATCH',
        f'sources/{public_source.id}',
        data={
            'ra': 234.22,
            'dec': -22.33,
            'altdata': {"dm": 28.5},
            'transient': False,
            'ra_dis': 2.3,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'sources/{public_source.id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    npt.assert_almost_equal(10 ** ((28.5 / 5) - 5), data['data']['luminosity_distance'])
    npt.assert_almost_equal(28.5, data['data']['dm'])
    npt.assert_almost_equal(
        10 ** ((28.5 / 5) - 5), data['data']['angular_diameter_distance']
    )


def test_parallax(upload_data_token, public_source):
    parallax = 0.001  # in arcsec = 1 kpc
    d_pc = 1 / parallax
    dm = 5.0 * np.log10(d_pc / (10.0))

    status, data = api(
        'PATCH',
        f'sources/{public_source.id}',
        data={
            'ra': 234.22,
            'dec': -22.33,
            'altdata': {"parallax": parallax},
            'transient': False,
            'ra_dis': 2.3,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'sources/{public_source.id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    npt.assert_almost_equal(dm, data['data']['dm'])


def test_low_redshift(upload_data_token, public_source):
    status, data = api(
        'PATCH',
        f'sources/{public_source.id}',
        data={
            'ra': 234.22,
            'dec': -22.33,
            'transient': False,
            'ra_dis': 2.3,
            'redshift': 0.00001,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'sources/{public_source.id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    assert data['data']['dm'] is None


def test_cannot_update_source_without_permission(view_only_token, public_source):
    status, data = api(
        'PATCH',
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


def test_cannot_post_source_with_null_radec(
    upload_data_token, view_only_token, public_group
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': None,
            'dec': None,
            'redshift': 3,
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400


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


def test_starlist(upload_data_token, public_source):
    status, data = api(
        'PATCH',
        f'sources/{public_source.id}',
        data={'ra': 234.22, 'dec': 22.33},
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET',
        f'sources/{public_source.id}/offsets?facility=P200&how_many=1',
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']["noffsets"] == 1
    assert data['data']['queries_issued'] == 1
    assert data['data']["facility"] == 'P200'
    assert 'starlist_str' in data['data']
    assert isinstance(data['data']["starlist_info"][0]["ra"], float)

    status, data = api(
        'GET', f'sources/{public_source.id}/offsets', token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']["noffsets"] == 3
    assert data['data']["facility"] == 'Keck'
    assert 'starlist_str' in data['data']
    assert isinstance(data['data']["starlist_info"][2]["dec"], float)

    ztf_star_position = data['data']["starlist_info"][2]["dec"]

    # use DR2 for offsets ... it should not be identical position as DR2
    status, data = api(
        'GET',
        f'sources/{public_source.id}/offsets?use_ztfref=false',
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert isinstance(data['data']["starlist_info"][2]["dec"], float)
    gaiadr2_star_position = data['data']["starlist_info"][2]["dec"]
    with pytest.raises(AssertionError):
        npt.assert_almost_equal(gaiadr2_star_position, ztf_star_position, decimal=10)


@pytest.mark.xfail(strict=False)
def test_finder(upload_data_token, public_source):
    status, data = api(
        'PATCH',
        f'sources/{public_source.id}',
        data={'ra': 234.22, 'dec': -22.33},
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    response = api(
        'GET',
        f'sources/{public_source.id}/finder?imsize=2',
        token=upload_data_token,
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
        token=upload_data_token,
    )
    assert status == 400

    # try an image too big
    status, data = api(
        'GET', f'sources/{public_source.id}/finder?imsize=30', token=upload_data_token,
    )
    assert status == 400


def test_source_notifications_unauthorized(
    source_notification_user_token, public_group, public_source
):
    status, data = api(
        "POST",
        "source_notifications",
        data={
            "groupIds": [public_group.id],
            "sourceId": public_source.id,
            "level": "hard",
            "additionalNotes": "",
        },
        token=source_notification_user_token,
    )
    assert status == 400
    # Test server should have no valid Twilio API credentials
    assert data["message"].startswith(
        "Twilio Communication SMS API authorization error"
    )
