from baselayer.app.env import load_env
from skyportal.tests import api
import numpy as np
import sncosmo
import math


_, cfg = load_env()


def test_token_user_post_get_photometry_data(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'

    assert data['data']['ra'] is None
    assert data['data']['dec'] is None
    assert data['data']['ra_unc'] is None
    assert data['data']['dec_unc'] is None

    np.testing.assert_allclose(
        data['data']['flux'], 12.24 * 10 ** (-0.4 * (25.0 - 23.9))
    )


def test_token_user_post_put_photometry_data(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'instrument_id': ztf_camera.id,
            "mjd": [59400, 59401, 59402],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "lol", "lol"],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    ids = data["data"]["ids"]
    assert len(ids) == 3

    # POSTing photometry that contains the same first two points should fail:
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'instrument_id': ztf_camera.id,
            "mjd": [59400, 59401, 59402],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "lol", "lol"],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'

    # PUTing photometry that contains
    # the same first point, the second point with a different origin, and a new third point should succeed
    # only the last two points will be ingested
    status, data = api(
        'PUT',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'instrument_id': ztf_camera.id,
            "mjd": [59400, 59401, 59402],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "omg", "lol"],
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    new_ids = data["data"]["ids"]
    assert len(new_ids) == 3
    assert len(set(new_ids).intersection(set(ids))) == 1


def test_token_user_post_put_get_photometry_data(
    upload_data_token_two_groups, public_source, public_group, public_group2, ztf_camera
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'instrument_id': ztf_camera.id,
            "mjd": [59400, 59401, 59402],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "lol", "lol"],
            'group_ids': [public_group.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data['status'] == 'success'
    ids = data["data"]["ids"]
    assert len(ids) == 3

    status, data = api(
        'GET', f'photometry/{ids[0]}?format=flux', token=upload_data_token_two_groups
    )
    assert status == 200
    assert data['status'] == 'success'
    group_ids = [g["id"] for g in data['data']['groups']]
    assert len(group_ids) == 1
    assert group_ids[0] == public_group.id

    # PUTing photometry that contains
    # the same first point, the second point with a different origin, and a new third point should succeed
    # only the last two points will be ingested
    status, data = api(
        'PUT',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'instrument_id': ztf_camera.id,
            "mjd": [59400, 59401],
            "mag": [19.2, 19.3],
            "magerr": [0.05, 0.06],
            "limiting_mag": [20.0, 20.1],
            "magsys": ["ab", "ab"],
            "filter": ["ztfr", "ztfg"],
            "ra": [42.01, 42.01],
            "dec": [42.02, 42.01],
            "origin": [None, "lol"],
            'group_ids': [public_group.id, public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data['status'] == 'success'
    new_ids = data["data"]["ids"]
    assert len(new_ids) == 2
    assert len(set(new_ids).intersection(set(ids))) == 2

    status, data = api(
        'GET', f'photometry/{ids[0]}?format=flux', token=upload_data_token_two_groups
    )
    assert status == 200
    assert data['status'] == 'success'
    group_ids = [g["id"] for g in data['data']['groups']]
    assert len(group_ids) == 2
    assert group_ids == [public_group.id, public_group2.id]


def test_post_photometry_multiple_groups(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group,
    public_group2,
    ztf_camera,
):
    upload_data_token = upload_data_token_two_groups
    public_source = public_source_two_groups
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id, public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'

    assert data['data']['ra'] is None
    assert data['data']['dec'] is None
    assert data['data']['ra_unc'] is None
    assert data['data']['dec_unc'] is None

    assert len(data['data']['groups']) == 2

    np.testing.assert_allclose(
        data['data']['flux'], 12.24 * 10 ** (-0.4 * (25.0 - 23.9))
    )


def test_post_photometry_all_groups(
    upload_data_token_two_groups,
    super_admin_token,
    public_source_two_groups,
    public_group,
    public_group2,
    ztf_camera,
):
    upload_data_token = upload_data_token_two_groups
    public_source = public_source_two_groups
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': "all",
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    assert data['data']['ra'] is None
    assert data['data']['dec'] is None
    assert data['data']['ra_unc'] is None
    assert data['data']['dec_unc'] is None

    assert len(data['data']['groups']) == 1
    assert data['data']['groups'][0]['name'] == cfg['misc']['public_group_name']

    np.testing.assert_allclose(
        data['data']['flux'], 12.24 * 10 ** (-0.4 * (25.0 - 23.9))
    )


def test_retrieve_photometry_group_membership_posted_by_other(
    upload_data_token_two_groups,
    view_only_token,
    public_source_two_groups,
    public_group,
    public_group2,
    ztf_camera,
):
    upload_data_token = upload_data_token_two_groups
    public_source = public_source_two_groups
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id, public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=view_only_token
    )
    assert status == 200
    assert data['status'] == 'success'

    assert data['data']['ra'] is None
    assert data['data']['dec'] is None
    assert data['data']['ra_unc'] is None
    assert data['data']['dec_unc'] is None

    np.testing.assert_allclose(
        data['data']['flux'], 12.24 * 10 ** (-0.4 * (25.0 - 23.9))
    )


def test_retrieve_photometry_error_group_membership_posted_by_other(
    upload_data_token_two_groups,
    view_only_token,
    public_source_two_groups,
    public_group,
    public_group2,
    ztf_camera,
):
    upload_data_token = upload_data_token_two_groups
    public_source = public_source_two_groups
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=view_only_token
    )
    # `view_only_token only` belongs to `public_group`, not `public_group2`
    assert status == 400
    assert data['status'] == 'error'
    assert "Insufficient permissions" in data['message']


def test_cannot_post_photometry_no_groups(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'
    assert "group_ids" in data["message"]


def test_cannot_post_photometry_empty_groups_list(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'
    assert "Invalid group_ids field" in data["message"]


def test_token_user_post_mag_photometry_data_and_convert(
    upload_data_token, public_source, ztf_camera, public_group
):

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': 21.0,
            'magerr': 0.2,
            'limiting_mag': 22.3,
            'magsys': 'vega',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'

    ab = sncosmo.get_magsystem('ab')
    vega = sncosmo.get_magsystem('vega')
    correction = 2.5 * np.log10(vega.zpbandflux('ztfg') / ab.zpbandflux('ztfg'))

    np.testing.assert_allclose(
        data['data']['flux'], 10 ** (-0.4 * (21.0 - correction - 23.9))
    )

    np.testing.assert_allclose(
        data['data']['fluxerr'], 0.2 / (2.5 / np.log(10)) * data['data']['flux']
    )

    status, data = api('GET', f'photometry/{photometry_id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    np.testing.assert_allclose(data['data']['mag'], 21.0 - correction)

    np.testing.assert_allclose(data['data']['magerr'], 0.2)


def test_token_user_post_and_get_different_systems_mag(
    upload_data_token, public_source, ztf_camera, public_group
):

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': 21.0,
            'magerr': 0.2,
            'limiting_mag': 22.3,
            'magsys': 'vega',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET',
        f'photometry/{photometry_id}?format=mag&magsys=vega',
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['magsys'] == 'vega'

    ab = sncosmo.get_magsystem('ab')
    vega = sncosmo.get_magsystem('vega')
    correction = 2.5 * np.log10(vega.zpbandflux('ztfg') / ab.zpbandflux('ztfg'))

    np.testing.assert_allclose(data['data']['mag'], 21.0)
    np.testing.assert_allclose(data['data']['magerr'], 0.2)
    np.testing.assert_allclose(data['data']['limiting_mag'], 22.3)

    status, data = api(
        'GET',
        f'photometry/{photometry_id}?format=mag&magsys=ab',
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    np.testing.assert_allclose(data['data']['mag'], 21.0 - correction)
    np.testing.assert_allclose(data['data']['magerr'], 0.2)
    np.testing.assert_allclose(data['data']['limiting_mag'], 22.3 - correction)


def test_token_user_post_and_get_different_systems_flux(
    upload_data_token, public_source, ztf_camera, public_group
):

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': 21.0,
            'magerr': 0.2,
            'limiting_mag': 22.3,
            'magsys': 'vega',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET',
        f'photometry/{photometry_id}?format=flux&magsys=vega',
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    ab = sncosmo.get_magsystem('ab')
    vega = sncosmo.get_magsystem('vega')
    correction = 2.5 * np.log10(vega.zpbandflux('ztfg') / ab.zpbandflux('ztfg'))

    np.testing.assert_allclose(
        data['data']['flux'], 10 ** (-0.4 * (21 - correction - 23.9))
    )
    np.testing.assert_allclose(
        data['data']['fluxerr'], 0.2 / (2.5 / np.log(10)) * data['data']['flux']
    )
    np.testing.assert_allclose(data['data']['zp'], 23.9 + correction)

    status, data = api(
        'GET',
        f'photometry/{photometry_id}?format=flux&magsys=ab',
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    np.testing.assert_allclose(
        data['data']['flux'], 10 ** (-0.4 * (21 - correction - 23.9))
    )
    np.testing.assert_allclose(
        data['data']['fluxerr'], 0.2 / (2.5 / np.log(10)) * data['data']['flux']
    )
    np.testing.assert_allclose(data['data']['zp'], 23.9)


def test_token_user_mixed_photometry_post(
    upload_data_token, public_source, ztf_camera, public_group
):

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': 21.0,
            'magerr': [0.2, 0.1],
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][1]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'

    np.testing.assert_allclose(data['data']['flux'], 10 ** (-0.4 * (21.0 - 23.9)))

    np.testing.assert_allclose(
        data['data']['fluxerr'], 0.1 / (2.5 / np.log(10)) * data['data']['flux']
    )

    # should fail as len(mag) != len(magerr)
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': [21.0],
            'magerr': [0.2, 0.1],
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_mixed_mag_none_photometry_post(
    upload_data_token, public_source, ztf_camera, public_group
):

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': None,
            'magerr': [0.2, 0.1],
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': [21.3, None],
            'magerr': [0.2, 0.1],
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': [21.3, None],
            'magerr': [None, 0.1],
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_post_photometry_limits(
    upload_data_token, public_source, ztf_camera, public_group
):

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': None,
            'magerr': None,
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'

    assert data['data']['flux'] is None
    np.testing.assert_allclose(
        data['data']['fluxerr'], 10 ** (-0.4 * (22.3 - 23.9)) / 5
    )

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': None,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'

    assert data['data']['flux'] is None
    np.testing.assert_allclose(
        data['data']['fluxerr'], 0.031 * 10 ** (-0.4 * (25.0 - 23.9))
    )


def test_token_user_post_invalid_filter(
    upload_data_token, public_source, ztf_camera, public_group
):

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': None,
            'magerr': None,
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'bessellv',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_post_photometry_data_series(
    upload_data_token, public_source, ztf_camera, public_group
):
    # valid request
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': [58000.0, 58001.0, 58002.0],
            'instrument_id': ztf_camera.id,
            'flux': [12.24, 15.24, 12.24],
            'fluxerr': [0.031, 0.029, 0.030],
            'filter': ['ztfg', 'ztfg', 'ztfg'],
            'zp': [25.0, 30.0, 21.2],
            'magsys': ['ab', 'ab', 'ab'],
            'ra': 264.1947917,
            'dec': [50.5478333, 50.5478333 + 0.00001, 50.5478333],
            'dec_unc': 0.2,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['ids']) == 3

    photometry_id = data['data']['ids'][1]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'
    assert np.allclose(data['data']['flux'], 15.24 * 10 ** (-0.4 * (30 - 23.9)))

    assert np.allclose(data['data']['dec'], 50.5478333 + 0.00001)

    assert np.allclose(data['data']['dec_unc'], 0.2)
    assert data['data']['ra_unc'] is None

    # invalid request
    status, data = api(
        'POST',
        'photometry',
        data=[
            {
                'obj_id': str(public_source.id),
                'mjd': 58000,
                'instrument_id': ztf_camera.id,
                'flux': 12.24,
                'fluxerr': 0.031,
                'filter': 'ztfg',
                'zp': 25.0,
                'magsys': 'ab',
                'group_ids': [public_group.id],
            },
            {
                'obj_id': str(public_source.id),
                'mjd': 58001,
                'instrument_id': ztf_camera.id,
                'flux': 15.24,
                'fluxerr': 0.031,
                'filter': 'ztfg',
                'zp': 30.0,
                'magsys': 'ab',
                'group_ids': [public_group.id],
            },
            {
                'obj_id': str(public_source.id),
                'mjd': 58002,
                'instrument_id': ztf_camera.id,
                'flux': 12.24,
                'fluxerr': 0.031,
                'filter': 'ztfg',
                'zp': 21.2,
                'magsys': 'vega',
                'group_ids': [public_group.id],
            },
        ],
        token=upload_data_token,
    )

    assert status == 400
    assert data['status'] == 'error'


def test_post_photometry_no_access_token(
    view_only_token, public_source, ztf_camera, public_group
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=view_only_token,
    )
    assert status == 400
    assert data['status'] == 'error'


def test_token_user_update_photometry(
    upload_data_token, manage_sources_token, public_source, ztf_camera, public_group
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfi',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'
    np.testing.assert_allclose(data['data']['flux'], 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    status, data = api(
        'PATCH',
        f'photometry/{photometry_id}',
        data={
            'obj_id': str(public_source.id),
            'flux': 11.0,
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfi',
        },
        token=manage_sources_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    np.testing.assert_allclose(data['data']['flux'], 11.0 * 10 ** (-0.4 * (25 - 23.9)))


def test_token_user_update_photometry_groups(
    upload_data_token_two_groups,
    manage_sources_token_two_groups,
    public_source_two_groups,
    ztf_camera,
    public_group,
    public_group2,
    view_only_token,
):
    upload_data_token = upload_data_token_two_groups
    manage_sources_token = manage_sources_token_two_groups
    public_source = public_source_two_groups

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfi',
            'group_ids': [public_group.id, public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=view_only_token
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'PATCH',
        f'photometry/{photometry_id}',
        data={
            'obj_id': str(public_source.id),
            'flux': 11.0,
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfi',
            'group_ids': [public_group2.id],
        },
        token=manage_sources_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=view_only_token
    )
    assert status == 400
    assert data['status'] == 'error'
    assert "Insufficient permissions" in data["message"]


def test_delete_photometry_data(
    upload_data_token, manage_sources_token, public_source, ztf_camera, public_group
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfi',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'
    np.testing.assert_allclose(data['data']['flux'], 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    status, data = api(
        'DELETE', f'photometry/{photometry_id}', token=manage_sources_token
    )
    assert status == 200

    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 400


def test_token_user_retrieving_source_photometry_and_convert(
    view_only_token, public_source
):
    status, data = api(
        'GET',
        f'sources/{public_source.id}/photometry?format=flux&magsys=ab',
        token=view_only_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert isinstance(data['data'], list)
    assert 'mjd' in data['data'][0]
    assert 'ra_unc' in data['data'][0]

    mag1_ab = -2.5 * np.log10(data['data'][0]['flux']) + data['data'][0]['zp']
    magerr1_ab = 2.5 / np.log(10) * data['data'][0]['fluxerr'] / data['data'][0]['flux']

    maglast_ab = -2.5 * np.log10(data['data'][-1]['flux']) + data['data'][-1]['zp']
    magerrlast_ab = (
        2.5 / np.log(10) * data['data'][-1]['fluxerr'] / data['data'][-1]['flux']
    )

    status, data = api(
        'GET',
        f'sources/{public_source.id}/photometry?format=mag&magsys=ab',
        token=view_only_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    assert np.allclose(mag1_ab, data['data'][0]['mag'])
    assert np.allclose(magerr1_ab, data['data'][0]['magerr'])

    assert np.allclose(maglast_ab, data['data'][-1]['mag'])
    assert np.allclose(magerrlast_ab, data['data'][-1]['magerr'])

    status, data = api(
        'GET',
        f'sources/{public_source.id}/photometry?format=flux&magsys=vega',
        token=view_only_token,
    )

    mag1_vega = -2.5 * np.log10(data['data'][0]['flux']) + data['data'][0]['zp']
    magerr1_vega = (
        2.5 / np.log(10) * data['data'][0]['fluxerr'] / data['data'][0]['flux']
    )

    maglast_vega = -2.5 * np.log10(data['data'][-1]['flux']) + data['data'][-1]['zp']
    magerrlast_vega = (
        2.5 / np.log(10) * data['data'][-1]['fluxerr'] / data['data'][-1]['flux']
    )

    assert status == 200
    assert data['status'] == 'success'

    ab = sncosmo.get_magsystem('ab')
    vega = sncosmo.get_magsystem('vega')
    vega_to_ab = {
        filter: 2.5 * np.log10(ab.zpbandflux(filter) / vega.zpbandflux(filter))
        for filter in ['ztfg', 'ztfr', 'ztfi']
    }

    assert np.allclose(mag1_ab, mag1_vega + vega_to_ab[data['data'][0]['filter']])
    assert np.allclose(magerr1_ab, magerr1_vega)

    assert np.allclose(
        maglast_ab, maglast_vega + vega_to_ab[data['data'][-1]['filter']]
    )
    assert np.allclose(magerrlast_ab, magerrlast_vega)


def test_token_user_retrieve_null_photometry(
    upload_data_token, public_source, ztf_camera, public_group
):

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': None,
            'magerr': None,
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    photometry_id = data['data']['ids'][0]
    status, data = api(
        'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['flux'] is None

    np.testing.assert_allclose(
        data['data']['fluxerr'], 10 ** (-0.4 * (22.3 - 23.9)) / 5.0
    )

    status, data = api(
        'GET', f'photometry/{photometry_id}?format=mag', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['mag'] is None
    assert data['data']['magerr'] is None


def test_token_user_big_post(
    upload_data_token, public_source, ztf_camera, public_group
):

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': [58000 + i for i in range(50000)],
            'instrument_id': ztf_camera.id,
            'mag': np.random.uniform(low=18, high=22, size=50000).tolist(),
            'magerr': np.random.uniform(low=0.1, high=0.3, size=50000).tolist(),
            'limiting_mag': 22.3,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'


def test_token_user_get_range_photometry(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': [58000.0, 58500.0, 59000.0],
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET',
        f'photometry/range',
        token=upload_data_token,
        data={'instrument_ids': [ztf_camera.id], 'max_date': '2018-05-15T00:00:00'},
    )
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']) == 1

    status, data = api(
        'GET',
        f'photometry/range?format=flux&magsys=vega',
        token=upload_data_token,
        data={'instrument_ids': [ztf_camera.id], 'max_date': '2019-02-01T00:00:00'},
    )
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']) == 2


def test_reject_photometry_inf(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': [58000.0, 58500.0, 59000.0],
            'instrument_id': ztf_camera.id,
            'flux': math.inf,
            'fluxerr': math.inf,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )

    assert status == 400
    assert data['status'] == 'error'

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': math.inf,
            'magerr': math.inf,
            'limiting_mag': 22.3,
            'magsys': 'vega',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )

    assert status == 400
    assert data['status'] == 'error'

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': 2.0,
            'magerr': 23.0,
            'limiting_mag': math.inf,
            'magsys': 'vega',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )

    assert status == 400
    assert data['status'] == 'error'

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': 58000.0,
            'instrument_id': ztf_camera.id,
            'mag': None,
            'magerr': None,
            'limiting_mag': -math.inf,
            'magsys': 'vega',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )

    assert status == 400
    assert data['status'] == 'error'

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': [58000.0, 58500.0, 59000.0],
            'instrument_id': ztf_camera.id,
            'flux': None,
            'fluxerr': math.inf,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )

    assert status == 400
    assert data['status'] == 'error'
