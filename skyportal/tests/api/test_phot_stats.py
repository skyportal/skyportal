import numpy as np
import traceback
from skyportal.tests import api
from baselayer.app.env import load_env
import uuid

_, cfg = load_env()
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]


def test_phot_stats_permissions(upload_data_token, super_admin_token, public_source):
    # normal user cannot delete or update the phot stats
    status, data = api(
        'DELETE', f'sources/{public_source.id}/phot_stat', token=upload_data_token
    )
    assert status == 401
    assert "Unauthorized" in data['message']

    status, data = api(
        'PUT',
        f'sources/{public_source.id}/phot_stat',
        token=upload_data_token,
        data={},
    )
    assert status == 401
    assert "Unauthorized" in data['message']

    status, data = api(
        'GET',
        f'sources/{public_source.id}/phot_stat',
        token=upload_data_token,
        data={},
    )
    assert status == 200
    # super user can delete the phot stats
    status, data = api(
        'DELETE', f'sources/{public_source.id}/phot_stat', token=super_admin_token
    )
    assert status == 200

    # normal user cannot post a phot stat
    status, data = api(
        'POST',
        f'sources/{public_source.id}/phot_stat',
        token=upload_data_token,
        data={},
    )
    assert status == 401
    assert "Unauthorized" in data['message']

    # super user can post a phot stat
    status, data = api(
        'POST',
        f'sources/{public_source.id}/phot_stat',
        token=super_admin_token,
        data={},
    )
    assert status == 200

    status, data = api(
        'GET',
        f'sources/{public_source.id}/phot_stat',
        token=upload_data_token,
        data={},
    )
    assert status == 200
    # super admin cannot re-post a phot stat

    status, data = api(
        'POST',
        f'sources/{public_source.id}/phot_stat',
        token=super_admin_token,
        data={},
    )
    assert status == 400
    assert "already exists" in data['message']


def test_delete_phot_stat_does_not_cascade(
    upload_data_token, super_admin_token, public_source
):
    status, data = api(
        'GET',
        f'sources/{public_source.id}/photometry',
        token=upload_data_token,
    )
    assert status == 200
    phot_ids = [p['id'] for p in data['data']]

    status, data = api(
        'DELETE', f'sources/{public_source.id}/phot_stat', token=super_admin_token
    )
    assert status == 200

    status, data = api(
        'GET',
        f'sources/{public_source.id}/phot_stat',
        token=upload_data_token,
        data={},
    )
    assert status == 400

    status, data = api(
        'GET',
        f'sources/{public_source.id}',
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == public_source.id

    status, data = api(
        'GET',
        f'sources/{public_source.id}/photometry',
        token=upload_data_token,
    )
    assert status == 200
    assert {p['id'] for p in data['data']} == set(phot_ids)


def test_phot_stats_for_public_source(upload_data_token, public_source):
    status, data = api(
        'GET',
        f'sources/{public_source.id}/photometry',
        token=upload_data_token,
    )
    assert status == 200
    photometry = data['data']
    mag = [p['mag'] for p in photometry]
    assert all(type(m) == float and not np.isnan(m) for m in mag)
    mag = np.array(mag)
    mjd = np.array([p['mjd'] for p in photometry])
    filt = np.array([p['filter'] for p in photometry])
    det = np.array([p['snr'] > PHOT_DETECTION_THRESHOLD for p in photometry])
    lim = np.array([p['limiting_mag'] for p in photometry])

    status, data = api(
        'GET',
        f'sources/{public_source.id}/phot_stat',
        token=upload_data_token,
        data={},
    )
    assert status == 200
    check_phot_stat_is_consistent(data['data'], mjd, mag, filt, det, lim)


def test_phot_stat_consistent(
    upload_data_token, super_admin_token, public_group, ztf_camera
):
    source_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": source_id,
            "ra": np.random.uniform(0, 360),
            "dec": np.random.uniform(-90, 90),
            "redshift": np.random.uniform(0, 1),
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    num_points = 20
    mjd = np.random.uniform(55000, 56000, num_points)
    mjd.sort()

    flux = np.random.normal(300, 10, num_points)
    flux[0:5] = 10.1

    filt = np.random.choice(['ztfg', 'ztfr', 'ztfi'], num_points)

    # post all these points
    phot_ids = []
    insert_idx = list(range(num_points))
    np.random.shuffle(insert_idx)  # input data in random order
    for i in insert_idx:
        status, data = api(
            'POST',
            'photometry',
            data={
                'obj_id': source_id,
                'mjd': mjd[i],
                'instrument_id': ztf_camera.id,
                'flux': flux[i],
                'fluxerr': 10.0,
                'zp': 25.0,
                'magsys': 'ab',
                'filter': filt[i],
                'group_ids': [public_group.id],
                'altdata': {'some_key': str(uuid.uuid4())},
            },
            token=upload_data_token,
        )
        if status != 200:
            print(data)
        assert status == 200
        assert data['status'] == 'success'
        phot_ids.append(data['data']['ids'][0])

    status, data = api(
        'GET',
        f'sources/{source_id}/photometry',
        token=upload_data_token,
    )
    assert status == 200
    photometry = data['data']
    assert len(photometry) == num_points

    # get the magnitudes, detections, and limits
    # in the order of MJD, not the order they were posted
    phot_dict = {p['mjd']: p for p in photometry}
    mag = []
    det = []
    lim = []
    for j in mjd:
        assert j in phot_dict
        mag.append(phot_dict[j]['mag'])
        det.append(phot_dict[j]['snr'] > PHOT_DETECTION_THRESHOLD)
        lim.append(phot_dict[j]['limiting_mag'])

    mag = np.array(mag)
    det = np.array(det)
    lim = np.array(lim)
    assert all(isinstance(m, float) and not np.isnan(m) for m in mag)
    assert np.sum(det) == num_points - 5

    status, data = api(
        'GET',
        f'sources/{source_id}/phot_stat',
        token=upload_data_token,
    )
    assert status == 200
    phot_stat = data['data']

    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)

    # now re-calculate the points
    status, data = api(
        'DELETE', f'sources/{source_id}/phot_stat', token=super_admin_token
    )
    assert status == 200

    status, data = api(
        'POST', f'sources/{source_id}/phot_stat', token=super_admin_token
    )
    assert status == 200

    status, data = api(
        'GET',
        f'sources/{source_id}/phot_stat',
        token=upload_data_token,
    )
    assert status == 200
    phot_stat = data['data']
    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)

    # now delete a point
    status, data = api('DELETE', f'photometry/{phot_ids[6]}', token=upload_data_token)
    phot_ids.pop(6)

    assert status == 200

    idx = np.ones(num_points, dtype=bool)
    # point inserted at index 6 is some other index
    # in the lists of mjd/mag/filt/det/lim values
    idx[insert_idx[6]] = False
    mjd_less = mjd[idx]
    mag_less = mag[idx]
    filt_less = filt[idx]
    det_less = det[idx]
    lim_less = lim[idx]

    status, data = api('GET', f'sources/{source_id}/phot_stat', token=upload_data_token)

    assert status == 200
    phot_stat = data['data']

    check_phot_stat_is_consistent(
        phot_stat, mjd_less, mag_less, filt_less, det_less, lim_less
    )

    # re-add that photometry point to check that the phot_stat updates
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': source_id,
            'mjd': mjd[insert_idx[6]],
            'instrument_id': ztf_camera.id,
            'flux': flux[insert_idx[6]],
            'fluxerr': 10.0,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': filt[insert_idx[6]],
            'group_ids': [public_group.id],
            'altdata': {'some_key': str(uuid.uuid4())},
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    phot_ids.insert(6, data['data']['ids'][0])

    status, data = api('GET', f'sources/{source_id}/phot_stat', token=upload_data_token)

    assert status == 200
    phot_stat = data['data']

    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)

    # modify one of the points and see if it updates
    flux[2] = 700.2
    status, data = api(
        'PATCH',
        f'photometry/{phot_ids[insert_idx.index(2)]}',
        data={
            'obj_id': source_id,
            'mjd': mjd[2],
            'instrument_id': ztf_camera.id,
            'flux': flux[2],
            'fluxerr': 10.0,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': filt[2],
            'group_ids': [public_group.id],
            'altdata': {'some_key': str(uuid.uuid4())},
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        'GET', f'photometry/{phot_ids[insert_idx.index(2)]}', token=upload_data_token
    )
    assert status == 200
    assert mjd[2] == data['data']['mjd']
    mag[2] = data['data']['mag']
    det[2] = data['data']['snr'] > PHOT_DETECTION_THRESHOLD

    status, data = api('GET', f'sources/{source_id}/phot_stat', token=upload_data_token)
    assert status == 200
    phot_stat = data['data']

    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)

    # add another photometry point via PUT
    flux = np.append(flux, np.random.normal(500, 10, 1))
    filt = np.append(filt, np.random.choice(['ztfg', 'ztfr', 'ztfi'], 1))

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': source_id,
            'mjd': 58000.0 + np.random.rand() * 100,
            'instrument_id': ztf_camera.id,
            'flux': flux[-1],
            'fluxerr': 10.0,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': filt[-1],
            'group_ids': [public_group.id],
            'altdata': {'some_key': str(uuid.uuid4())},
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    phot_ids.append(data['data']['ids'][0])

    status, data = api('GET', f'photometry/{phot_ids[-1]}', token=upload_data_token)
    assert status == 200
    mag = np.append(mag, data['data']['mag'])
    mjd = np.append(mjd, data['data']['mjd'])
    det = np.append(det, True)
    lim = np.append(lim, mag[-1])

    status, data = api('GET', f'sources/{source_id}/phot_stat', token=upload_data_token)
    assert status == 200
    phot_stat = data['data']

    check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim)


def check_phot_stat_is_consistent(phot_stat, mjd, mag, filt, det, lim):
    filter_set = set(filt)

    try:
        # check the number of observations/detections
        assert phot_stat['num_obs_global'] == len(mjd)
        assert phot_stat['num_det_global'] == len(mag[det])

        # per filter
        for f in filter_set:
            if len(mjd[filt == f]):
                assert phot_stat['num_obs_per_filter'][f] == len(mjd[filt == f])
            if len(mjd[det & (filt == f)]):
                assert phot_stat['num_det_per_filter'][f] == len(mjd[det & (filt == f)])

        # latest observation
        assert phot_stat['recent_obs_mjd'] == np.max(mjd)

        # check the first detection
        idx = np.argmin(mjd[det])
        assert phot_stat['first_detected_mjd'] == mjd[det][idx]
        assert phot_stat['first_detected_mag'] == mag[det][idx]
        assert phot_stat['first_detected_filter'] == filt[det][idx]

        # check the last detection
        idx = np.argmax(mjd[det])
        assert phot_stat['last_detected_mjd'] == mjd[det][idx]
        assert phot_stat['last_detected_mag'] == mag[det][idx]
        assert phot_stat['last_detected_filter'] == filt[det][idx]

        # check the mag mean, peak and rms
        assert np.isclose(phot_stat['mean_mag_global'], np.mean(mag[det]))
        assert np.isclose(phot_stat['peak_mag_global'], min(mag[det]))
        assert np.isclose(phot_stat['faintest_mag_global'], max(mag[det]))
        assert np.isclose(phot_stat['mag_rms_global'], np.std(mag[det]))

        for f in filter_set:
            if len(mag[det & (filt == f)]):
                assert np.isclose(
                    phot_stat['mean_mag_per_filter'][f], np.mean(mag[det & (filt == f)])
                )
                assert np.isclose(
                    phot_stat['peak_mag_per_filter'][f], min(mag[det & (filt == f)])
                )
                assert np.isclose(
                    phot_stat['faintest_mag_per_filter'][f], max(mag[det & (filt == f)])
                )
                assert np.isclose(
                    phot_stat['mag_rms_per_filter'][f], np.std(mag[det & (filt == f)])
                )

        # check the deepest limits (non-detections)
        if len(lim[~det]):
            assert phot_stat['deepest_limit_global'] == min(lim[~det])
        for f in filter_set:
            if len(lim[~det & (filt == f)]) > 0:
                assert phot_stat['deepest_limit_per_filter'][f] == min(
                    lim[~det & (filt == f)]
                )

        # check the color
        for f1 in filter_set:
            for f2 in filter_set:
                if f1 == f2:
                    continue
                if (
                    len(mag[det & (filt == f1)]) == 0
                    or len(mag[det & (filt == f2)]) == 0
                ):
                    continue
                mag1 = np.mean(mag[det & (filt == f1)])
                mag2 = np.mean(mag[det & (filt == f2)])
                assert np.isclose(phot_stat['mean_color'][f'{f1}-{f2}'], mag1 - mag2)

        date_array = np.array(
            list(zip(mjd, det)), dtype=[('mjd', 'float'), ('det', 'bool')]
        )
        date_array.sort(order='mjd')

        # the last non-detection:
        idx = np.argmax(date_array['det']) - 1
        if idx >= 0:
            dt = date_array['mjd'][idx + 1] - date_array['mjd'][idx]
            assert np.isclose(phot_stat['time_to_non_detection'], dt)
            assert phot_stat['last_non_detection_mjd'] == date_array['mjd'][idx]
        else:
            assert phot_stat['time_to_non_detection'] is None
            assert phot_stat['last_non_detection_mjd'] is None

    except Exception as e:
        from pprint import pprint

        print('Data from photometry points:')
        print(f'mag: {mag}')
        print(f'mjd: {mjd}')
        print(f'filt: {filt}')
        print(f'det: {det}')
        print(f'lim: {lim}')
        print('PhotStat object:')
        pprint(phot_stat)
        print(traceback.format_exc())
        raise e
