import os
import numpy as np

from skyportal.tests import api
from skyportal.utils.gcn import from_url

import time
import uuid
import pandas as pd
from regions import Regions
from astropy.table import Table


def test_gcn_GW(super_admin_token, view_only_token):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    dateobs = "2019-04-25 08:18:05"
    params = {"include2DMap": True}

    status, data = api('GET', f'gcn_event/{dateobs}', token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2019-04-25T08:18:05"
    assert 'GW' in data["tags"]

    skymap = "bayestar.fits.gz"
    status, data = api(
        'GET',
        f'localization/{dateobs}/name/{skymap}',
        token=super_admin_token,
        params=params,
    )

    data = data["data"]
    assert data["dateobs"] == "2019-04-25T08:18:05"
    assert data["localization_name"] == "bayestar.fits.gz"
    assert np.isclose(np.sum(data["flat_2d"]), 1)

    status, data = api(
        'DELETE',
        f'localization/{dateobs}/name/{skymap}',
        token=view_only_token,
    )
    assert status == 400

    status, data = api(
        'DELETE',
        f'localization/{dateobs}/name/{skymap}',
        token=super_admin_token,
    )
    assert status == 200


def test_gcn_Fermi(super_admin_token, view_only_token):

    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    dateobs = "2018-01-16 00:36:53"
    params = {"include2DMap": True}

    status, data = api('GET', f'gcn_event/{dateobs}', token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2018-01-16T00:36:53"
    assert 'GRB' in data["tags"]

    skymap = "214.74000_28.14000_11.19000"
    status, data = api(
        'GET',
        f'localization/{dateobs}/name/{skymap}',
        token=super_admin_token,
        params=params,
    )

    data = data["data"]
    assert data["dateobs"] == "2018-01-16T00:36:53"
    assert data["localization_name"] == "214.74000_28.14000_11.19000"
    assert np.isclose(np.sum(data["flat_2d"]), 1)

    status, data = api(
        'DELETE',
        f'localization/{dateobs}/name/{skymap}',
        token=view_only_token,
    )
    assert status == 400

    status, data = api(
        'DELETE',
        f'localization/{dateobs}/name/{skymap}',
        token=super_admin_token,
    )
    assert status == 200


def test_gcn_IPN(super_admin_token):

    skymap = f'{os.path.dirname(__file__)}/../data/GRB220617A_IPN_map_hpx.fits.gz'
    dateobs = '2022-06-17T18:31:12'
    tags = ['IPN', 'GRB']

    data = {'dateobs': dateobs, 'skymap': skymap, 'tags': tags}

    nretries = 0
    posted = False
    while nretries < 10 and not posted:
        status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
        if status == 200:
            posted = True
        else:
            nretries += 1
            time.sleep(3)

    assert nretries < 10
    assert posted is True
    assert status == 200
    assert data['status'] == 'success'

    dateobs = "2022-06-17 18:31:12"
    status, data = api('GET', f'gcn_event/{dateobs}', token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2022-06-17T18:31:12"
    assert 'IPN' in data["tags"]


def test_gcn_from_moc(super_admin_token, view_only_token):

    skymap = f'{os.path.dirname(__file__)}/../data/GRB220617A_IPN_map_hpx.fits.gz'
    dateobs = '2022-06-18T18:31:12'
    tags = ['IPN', 'GRB']
    skymap = from_url(skymap)

    data = {'dateobs': dateobs, 'skymap': skymap, 'tags': tags}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    dateobs = "2022-06-18 18:31:12"
    status, data = api('GET', f'gcn_event/{dateobs}', token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2022-06-18T18:31:12"
    assert 'IPN' in data["tags"]


def test_gcn_summary_sources(
    super_admin_user,
    super_admin_token,
    view_only_token,
    public_group,
    ztf_camera,
    upload_data_token,
):

    datafile = f'{os.path.dirname(__file__)}/../../../data/GW190814.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # wait for event to load
    for n_times in range(26):
        status, data = api(
            'GET', "gcn_event/2019-08-14T21:10:39", token=super_admin_token
        )
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 25

    # wait for the localization to load
    params = {"include2DMap": True}
    for n_times_2 in range(26):
        status, data = api(
            'GET',
            'localization/2019-08-14T21:10:39/name/LALInference.v1.fits.gz',
            token=super_admin_token,
            params=params,
        )

        if data['status'] == 'success':
            data = data["data"]
            assert data["dateobs"] == "2019-08-14T21:10:39"
            assert data["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert n_times_2 < 25

    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 24.6258,
            "dec": -32.9024,
            "redshift": 3,
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id,
            'mjd': 58709 + 1,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            "ra": 24.6258,
            "dec": -32.9024,
            "ra_unc": 0.01,
            "dec_unc": 0.01,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # get the gcn event summary
    params = {
        "title": "gcn summary",
        "subject": "follow-up",
        "userIds": super_admin_user.id,
        "groupId": public_group.id,
        "startDate": "2019-08-13 08:18:05",
        "endDate": "2019-08-19 08:18:05",
        "localizationCumprob": 0.99,
        "showSources": True,
        "showGalaxies": False,
        "showObservations": False,
        "noText": False,
    }

    status, data = api(
        'GET',
        'gcn_events/summary/2019-08-14T21:10:39',
        params=params,
        token=super_admin_token,
    )

    assert status == 200
    data = data["data"]

    assert "TITLE: GCN SUMMARY" in data[0]
    assert "SUBJECT: Follow-up" in data[1]
    assert "DATE" in data[2]
    assert (
        f"FROM:  {super_admin_user.first_name} {super_admin_user.last_name} at Affiliation <{super_admin_user.contact_email}>"
        in data[3]
    )
    assert (
        f"{super_admin_user.first_name.upper()[0]}. {super_admin_user.last_name} (Affiliation)"
        in data[4]
    )
    assert f"on behalf of the {public_group.name}, report:" in data[5]

    # sources
    assert (
        "Found" in data[6]
        and "in the event's localization, given the specified date range:" in data[6]
    )
    sources_table = data[7].split('\n')
    assert (
        len(sources_table) >= 6
    )  # other sources have probably been added in previous tests
    assert "id" in sources_table[1]
    assert "alias" in sources_table[1]
    assert "ra" in sources_table[1]
    assert "dec" in sources_table[1]
    assert "redshift" in sources_table[1]

    # source phot
    assert "Photometry for source" in data[8]
    source_table = data[9].split('\n')
    assert (
        len(source_table) >= 6
    )  # other photometry have probably been added in previous tests
    assert "mjd" in source_table[1]
    assert "ra" in source_table[1]
    assert "dec" in source_table[1]
    assert "mag±err (ab)" in source_table[1]
    assert "filter" in source_table[1]
    assert "origin" in source_table[1]
    assert "instrument" in source_table[1]


def test_gcn_summary_galaxies(
    super_admin_user,
    super_admin_token,
    view_only_token,
    public_group,
):

    catalog_name = 'test_galaxy_catalog'

    # in case the catalog already exists, delete it.
    status, data = api(
        'DELETE', f'galaxy_catalog/{catalog_name}', token=super_admin_token
    )

    datafile = f'{os.path.dirname(__file__)}/../../../data/GW190814.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # wait for event to load
    for n_times in range(26):
        status, data = api(
            'GET', "gcn_event/2019-08-14T21:10:39", token=super_admin_token
        )
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 25

    # wait for the localization to load
    params = {"include2DMap": True}
    for n_times_2 in range(26):
        status, data = api(
            'GET',
            'localization/2019-08-14T21:10:39/name/LALInference.v1.fits.gz',
            token=super_admin_token,
            params=params,
        )

        if data['status'] == 'success':
            data = data["data"]
            assert data["dateobs"] == "2019-08-14T21:10:39"
            assert data["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert n_times_2 < 25

    datafile = f'{os.path.dirname(__file__)}/../../../data/CLU_mini.hdf5'
    data = {
        'catalog_name': catalog_name,
        'catalog_data': Table.read(datafile).to_pandas().to_dict(orient='list'),
    }

    status, data = api('POST', 'galaxy_catalog', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    params = {'catalog_name': catalog_name}

    nretries = 0
    galaxies_loaded = False
    while nretries < 40:
        status, data = api(
            'GET', 'galaxy_catalog', token=view_only_token, params=params
        )
        assert status == 200
        data = data["data"]["galaxies"]
        if len(data) == 92 and any(
            [
                d['name'] == '6dFgs gJ0001313-055904'
                and d['mstar'] == 336.60756522868667
                for d in data
            ]
        ):
            galaxies_loaded = True
            break
        nretries = nretries + 1
        time.sleep(2)

    assert nretries < 40
    assert galaxies_loaded

    # get the gcn event summary
    params = {
        "title": "gcn summary",
        "subject": "follow-up",
        "userIds": super_admin_user.id,
        "groupId": public_group.id,
        "startDate": "2019-08-13 08:18:05",
        "endDate": "2019-08-19 08:18:05",
        "localizationCumprob": 0.99,
        "showSources": False,
        "showGalaxies": True,
        "showObservations": False,
        "noText": False,
    }

    status, data = api(
        'GET',
        'gcn_events/summary/2019-08-14T21:10:39',
        params=params,
        token=super_admin_token,
    )
    assert status == 200
    data = data["data"]

    assert "TITLE: GCN SUMMARY" in data[0]
    assert "SUBJECT: Follow-up" in data[1]
    assert "DATE" in data[2]
    assert (
        f"FROM:  {super_admin_user.first_name} {super_admin_user.last_name} at Affiliation <{super_admin_user.contact_email}>"
        in data[3]
    )
    assert (
        f"{super_admin_user.first_name.upper()[0]}. {super_admin_user.last_name} (Affiliation)"
        in data[4]
    )
    assert f"on behalf of the {public_group.name}, report:" in data[5]

    # galaxies
    assert "Found 82 galaxies in the event's localization:" in data[6]

    galaxy_table = data[7].split('\n')
    assert len(galaxy_table) == 87
    assert "catalog" in galaxy_table[1]
    assert "name" in galaxy_table[1]
    assert "ra" in galaxy_table[1]
    assert "dec" in galaxy_table[1]
    assert "distmpc" in galaxy_table[1]
    assert "redshift" in galaxy_table[1]

    status, data = api(
        'DELETE', f'galaxy_catalog/{catalog_name}', token=super_admin_token
    )


def test_gcn_summary_observations(
    super_admin_user,
    super_admin_token,
    public_group,
):

    datafile = f'{os.path.dirname(__file__)}/../../../data/GW190814.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    gcnevent_id = data['data']['gcnevent_id']

    # wait for event to load
    for n_times in range(26):
        status, data = api(
            'GET', "gcn_event/2019-08-14T21:10:39", token=super_admin_token
        )
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 25

    # wait for the localization to load
    params = {"include2DMap": True}
    for n_times_2 in range(26):
        status, data = api(
            'GET',
            'localization/2019-08-14T21:10:39/name/LALInference.v1.fits.gz',
            token=super_admin_token,
            params=params,
        )

        if data['status'] == 'success':
            data = data["data"]
            assert data["dateobs"] == "2019-08-14T21:10:39"
            assert data["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert n_times_2 < 25
    localization_id = data['id']

    name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': name,
            'nickname': name,
            'lat': 0.0,
            'lon': 0.0,
            'elevation': 0.0,
            'diameter': 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    fielddatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Fields.csv'
    regionsdatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Region.reg'

    instrument_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'instrument',
        data={
            'name': instrument_name,
            'type': 'imager',
            'band': 'Optical',
            'filters': ['ztfr'],
            'telescope_id': telescope_id,
            'api_classname': 'ZTFAPI',
            'api_classname_obsplan': 'ZTFMMAAPI',
            'field_data': pd.read_csv(fielddatafile)[199:204].to_dict(orient='list'),
            'field_region': Regions.read(regionsdatafile).serialize(format='ds9'),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    # wait for the fields to populate
    nretries = 0
    fields_loaded = False
    while not fields_loaded and nretries < 5:
        try:
            status, data = api(
                'GET',
                f'instrument/{instrument_id}',
                token=super_admin_token,
            )
            assert status == 200
            assert data['status'] == 'success'
            assert data['data']['band'] == 'NIR'

            assert len(data['data']['fields']) == 5
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    request_data = {
        'group_id': public_group.id,
        'instrument_id': instrument_id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
    }

    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    allocation_id = data['data']['id']

    queue_name = str(uuid.uuid4())
    request_data = {
        'allocation_id': allocation_id,
        'gcnevent_id': gcnevent_id,
        'localization_id': localization_id,
        'payload': {
            'start_date': '2019-08-15 08:18:05',
            'end_date': '2019-08-20 08:18:05',
            'filter_strategy': 'block',
            'schedule_strategy': 'tiling',
            'schedule_type': 'greedy_slew',
            'exposure_time': 300,
            "field_ids": [200, 201, 202],
            'filters': 'ztfr',
            'maximum_airmass': 2.0,
            'integrated_probability': 100,
            'minimum_time_difference': 30,
            'queue_name': queue_name,
            'program_id': 'Partnership',
            'subprogram_name': 'GRB',
        },
    }

    status, data = api(
        'POST', 'observation_plan', data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['ids'][0]

    # wait for the observation plan to finish loading
    time.sleep(15)

    status, data = api(
        'GET',
        f'observation_plan/{id}',
        params={"includePlannedObservations": "true"},
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    assert data["data"]["gcnevent_id"] == gcnevent_id
    assert data["data"]["allocation_id"] == allocation_id
    assert data["data"]["payload"] == request_data["payload"]

    assert len(data["data"]["observation_plans"]) == 1

    datafile = f'{os.path.dirname(__file__)}/../../../data/sample_observation_gw.csv'
    data = {
        'telescopeName': name,
        'instrumentName': instrument_name,
        'observationData': pd.read_csv(datafile).to_dict(orient='list'),
    }

    status, data = api('POST', 'observation', data=data, token=super_admin_token)

    assert status == 200
    assert data['status'] == 'success'

    # wait for the executed observations to populate

    params = {
        'telescopeName': name,
        'instrumentName': instrument_name,
        'startDate': '2019-08-13 08:18:05',
        'endDate': '2019-08-19 08:18:05',
    }
    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 25:
        try:
            status, data = api(
                'GET', 'observation', params=params, token=super_admin_token
            )
            assert status == 200
            data = data["data"]
            assert len(data['observations']) >= 9
            observations_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(2)

    assert nretries < 25
    assert status == 200
    assert observations_loaded is True

    # get the gcn event summary
    params = {
        "title": "gcn summary",
        "subject": "follow-up",
        "userIds": super_admin_user.id,
        "groupId": public_group.id,
        "startDate": "2019-08-13 08:18:05",
        "endDate": "2019-08-19 08:18:05",
        "localizationCumprob": 0.99,
        "showSources": False,
        "showGalaxies": False,
        "showObservations": True,
        "noText": False,
    }

    status, data = api(
        'GET',
        'gcn_events/summary/2019-08-14T21:10:39',
        params=params,
        token=super_admin_token,
    )
    assert status == 200
    data = data["data"]

    assert "TITLE: GCN SUMMARY" in data[0]
    assert "SUBJECT: Follow-up" in data[1]
    assert "DATE" in data[2]
    assert (
        f"FROM:  {super_admin_user.first_name} {super_admin_user.last_name} at Affiliation <{super_admin_user.contact_email}>"
        in data[3]
    )
    assert (
        f"{super_admin_user.first_name.upper()[0]}. {super_admin_user.last_name} (Affiliation)"
        in data[4]
    )
    assert f"on behalf of the {public_group.name}, report:" in data[5]

    # obs
    assert "Observations:" in data[6]

    obs_summary_text = 'We observed the localization region of LVC trigger 2019-08-14T21:10:39.000 UTC.  We obtained a total of 9 images covering ztfr bands for a total of 270 seconds. The observations covered 715.2 square degrees beginning at 2019-08-17T01:00:00.288 (2 days after the burst trigger time) corresponding to ~9% of the probability enclosed in the localization region.'
    assert obs_summary_text in data[7]

    obs_table = data[8].split('\n')
    assert len(obs_table) >= 14  # other obs have probably been added in previous tests
    assert "T-T0 (hr)" in obs_table[1]
    assert "mjd" in obs_table[1]
    assert "ra" in obs_table[1]
    assert "dec" in obs_table[1]
    assert "filter" in obs_table[1]
    assert "exposure" in obs_table[1]
    assert "limmag (ab)" in obs_table[1]


def test_confirm_reject_source_in_gcn(
    super_admin_token,
    view_only_token,
    ztf_camera,
    upload_data_token,
):

    datafile = f'{os.path.dirname(__file__)}/../../../data/GW190814.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # wait for event to load
    for n_times in range(26):
        status, data = api(
            'GET', "gcn_event/2019-08-14T21:10:39", token=super_admin_token
        )
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 25

    # wait for the localization to load
    params = {"include2DMap": True}
    for n_times_2 in range(26):
        status, data = api(
            'GET',
            'localization/2019-08-14T21:10:39/name/LALInference.v1.fits.gz',
            token=super_admin_token,
            params=params,
        )

        if data['status'] == 'success':
            data = data["data"]
            assert data["dateobs"] == "2019-08-14T21:10:39"
            assert data["localization_name"] == "LALInference.v1.fits.gz"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert n_times_2 < 25

    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 24.6258,
            "dec": -32.9024,
            "redshift": 3,
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id,
            'mjd': 58709 + 1,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
            "ra": 24.6258,
            "dec": -32.9024,
            "ra_unc": 0.01,
            "dec_unc": 0.01,
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    params = {
        "sourcesIdList": obj_id,
    }
    status, data = api(
        'GET',
        'sources_in_gcn/2019-08-14T21:10:39',
        params=params,
        token=upload_data_token,
    )
    assert status == 200
    assert len(data["data"]) == 0

    # confirm source
    params = {
        "source_id": obj_id,
        "localization_name": "LALInference.v1.fits.gz",
        "localization_cumprob": 0.95,
        "confirmed": True,
        "start_date": "2019-08-13 08:18:05",
        "end_date": "2019-08-19 08:18:05",
    }

    # verify that you can't confirm a source without the Manage GCNs permission
    status, data = api(
        'POST',
        'sources_in_gcn/2019-08-14T21:10:39',
        data=params,
        token=upload_data_token,
    )
    assert status == 401

    status, data = api(
        'POST',
        'sources_in_gcn/2019-08-14T21:10:39',
        data=params,
        token=super_admin_token,
    )
    assert status == 200

    params = {
        "sourcesIdList": obj_id,
    }
    status, data = api(
        'GET',
        'sources_in_gcn/2019-08-14T21:10:39',
        params=params,
        token=upload_data_token,
    )
    assert status == 200
    data = data["data"]
    assert len(data) == 1
    assert data[0]["obj_id"] == obj_id
    assert data[0]["dateobs"] == "2019-08-14T21:10:39"
    assert data[0]["confirmed"] is True

    # find gcns associated to source
    status, data = api(
        'GET',
        f"associated_gcns/{obj_id}",
        token=upload_data_token,
    )
    assert status == 200
    data = data["data"]
    assert '2019-08-14T21:10:39' in data['gcns']

    # reject source
    params = {
        "confirmed": False,
    }

    status, data = api(
        'PATCH',
        f'sources_in_gcn/2019-08-14T21:10:39/{obj_id}',
        data=params,
        token=upload_data_token,
    )
    assert status == 401

    status, data = api(
        'PATCH',
        f'sources_in_gcn/2019-08-14T21:10:39/{obj_id}',
        data=params,
        token=super_admin_token,
    )
    assert status == 200

    params = {
        "sourcesIdList": obj_id,
    }
    status, data = api(
        'GET',
        'sources_in_gcn/2019-08-14T21:10:39',
        params=params,
        token=upload_data_token,
    )
    assert status == 200
    data = data["data"]
    assert len(data) == 1
    assert data[0]["obj_id"] == obj_id
    assert data[0]["dateobs"] == "2019-08-14T21:10:39"
    assert data[0]["confirmed"] is False

    # verify that no gcns are associated to source

    # find no gcns associated to source
    status, data = api(
        'GET',
        f"associated_gcns/{obj_id}",
        token=upload_data_token,
    )
    assert status == 200
    data = data["data"]
    assert len(data['gcns']) == 0

    # mark source as unknow (delete it from the table)
    status, data = api(
        'DELETE',
        f'sources_in_gcn/2019-08-14T21:10:39/{obj_id}',
        token=upload_data_token,
    )
    assert status == 401

    status, data = api(
        'DELETE',
        f'sources_in_gcn/2019-08-14T21:10:39/{obj_id}',
        token=super_admin_token,
    )
    assert status == 200

    params = {
        "sourcesIdList": obj_id,
    }
    status, data = api(
        'GET',
        'sources_in_gcn/2019-08-14T21:10:39',
        params=params,
        token=upload_data_token,
    )
    assert status == 200
    data = data["data"]
    assert len(data) == 0
