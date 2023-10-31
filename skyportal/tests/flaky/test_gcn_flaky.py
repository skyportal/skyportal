import os
import numpy as np

from skyportal.tests import api

import time
import uuid
import pandas as pd
from regions import Regions


def test_gcn_summary_observations(
    super_admin_user, super_admin_token, view_only_token, public_group
):

    datafile = f'{os.path.dirname(__file__)}/../../../../data/GW190814.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    event_data = {'xml': payload}

    dateobs = "2019-08-14T21:10:39"
    status, data = api('GET', f'gcn_event/{dateobs}', token=super_admin_token)

    if status == 404:
        status, data = api(
            'POST', 'gcn_event', data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data['status'] == 'success'

        gcnevent_id = data['data']['gcnevent_id']
    else:
        gcnevent_id = data['data']['id']

    # wait for event to load
    for n_times in range(26):
        status, data = api('GET', f"gcn_event/{dateobs}", token=super_admin_token)
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

    fielddatafile = f'{os.path.dirname(__file__)}/../../../../data/ZTF_Fields.csv'
    regionsdatafile = f'{os.path.dirname(__file__)}/../../../../data/ZTF_Region.reg'

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

    # wait for the observation plan to finish loading
    time.sleep(15)
    n_retries = 0
    while n_retries < 10:
        try:
            status, data = api(
                'GET',
                'observation_plan',
                params={"includePlannedObservations": "true"},
                token=super_admin_token,
            )
            assert status == 200
            assert data['status'] == 'success'

            data = [
                d
                for d in data['data']['requests']
                if d['gcnevent_id'] == gcnevent_id
                and d['allocation_id'] == allocation_id
            ]
            assert len(data) == 1
            assert data[0]["payload"] == request_data["payload"]
            assert len(data[0]["observation_plans"]) == 1
            break
        except AssertionError:
            n_retries = n_retries + 1
            time.sleep(3)

        assert n_retries < 10

    datafile = f'{os.path.dirname(__file__)}/../../../../data/sample_observation_gw.csv'
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
    data = {
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
        'POST',
        'gcn_event/2019-08-14T21:10:39/summary',
        data=data,
        token=super_admin_token,
    )
    assert status == 200
    summary_id = data["data"]["id"]

    nretries = 0
    summaries_loaded = False
    while nretries < 40:
        status, data = api(
            'GET',
            f'gcn_event/2019-08-14T21:10:39/summary/{summary_id}',
            token=view_only_token,
            params=params,
        )
        if status == 404:
            nretries = nretries + 1
            time.sleep(5)
        if status == 200:
            data = data["data"]
            if data["text"] == "pending":
                nretries = nretries + 1
                time.sleep(5)
            else:
                summaries_loaded = True
                break

    assert nretries < 40
    assert summaries_loaded
    data = list(filter(None, data["text"].split("\n")))

    assert "TITLE: GCN SUMMARY" in data[0]
    assert "SUBJECT: Follow-up" in data[1]
    assert "DATE" in data[2]
    assert (
        f"FROM:  {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
        in data[3]
    )
    assert (
        f"{super_admin_user.first_name.upper()[0]}. {super_admin_user.last_name} (...)"
        in data[4]
    )
    assert f"on behalf of the {public_group.name}, report:" in data[5]

    # obs
    assert "Observations:" in data[6]

    obs_summary_text = (
        'We observed the localization region of LVC trigger 2019-08-14T21:10:39.000 UTC.  '
        'We obtained a total of 9 images covering ztfr bands for a total of 270 seconds. '
        'The observations covered 26.5 square degrees of the localization at least once, beginning at 2019-08-17T01:00:00.288 '
        '(2 days after the burst trigger time) corresponding to ~9% '
        'of the probability enclosed in the localization region.'
    )

    assert obs_summary_text in data[8]

    obs_table = data[10:]
    assert len(obs_table) >= 13  # other obs have probably been added in previous tests
    assert "T-T0 (hr)" in obs_table[1]
    assert "mjd" in obs_table[1]
    assert "ra" in obs_table[1]
    assert "dec" in obs_table[1]
    assert "filter" in obs_table[1]
    assert "exposure" in obs_table[1]
    assert "limmag (ab)" in obs_table[1]
