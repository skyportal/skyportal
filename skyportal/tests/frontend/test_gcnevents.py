import os
import uuid
import pytest
from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_gcnevents(
    driver, user, super_admin_token, upload_data_token, view_only_token, ztf_camera
):

    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 229.9620403,
            "dec": 34.8442757,
            "redshift": 3,
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id,
            'mjd': 58134.025611226854 + 1,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200

    driver.get(f'/become_user/{user.id}')
    driver.get('/gcn_events/2018-01-16T00:36:53')

    driver.wait_for_xpath('//*[text()="180116 00:36:53"]')
    driver.wait_for_xpath('//*[text()="Fermi"]')
    driver.wait_for_xpath('//*[text()="GRB"]')

    driver.wait_for_xpath(f'//*[text()="{obj_id}"]')
