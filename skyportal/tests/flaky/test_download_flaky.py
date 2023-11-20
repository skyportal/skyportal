import os
import numpy as np
from numpy import random

from skyportal.tests import api
import time
import uuid
import pandas as pd
from regions import Regions
from astropy.table import Table

from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from baselayer.app.config import load_config
from os.path import join as pjoin

import pytest

cfg = load_config()


def enter_comment_text(driver, comment_text):
    comment_xpath = "//div[@data-testid='comments-accordion']//textarea[@name='text']"
    comment_box = driver.wait_for_xpath(comment_xpath)
    driver.click_xpath(comment_xpath)
    comment_box.send_keys(comment_text)


def test_download_sources(
    driver, user, public_group, upload_data_token, annotation_token
):
    # generate a list of 20 source ids:
    source_ids = [str(uuid.uuid4()) for i in range(20)]
    origin = str(uuid.uuid4())
    # post 20 sources:
    for source_id in source_ids:
        status, data = api(
            "POST",
            "sources",
            data={
                "id": source_id,
                # random ra value
                "ra": random.random() * 360 - 180,
                "dec": random.random() * 180 - 90,
                "redshift": 3,
                "transient": False,
                "ra_dis": 2.3,
                "origin": origin,
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200

    for source_id in source_ids:
        status, data = api(
            'POST',
            f'sources/{source_id}/annotations',
            data={
                'origin': 'kowalski',
                'data': {'offset_from_host_galaxy': 1.5},
                'group_ids': [public_group.id],
            },
            token=annotation_token,
        )
        assert status == 200

    for source_id in source_ids:
        status, data = api(
            'POST',
            f'sources/{source_id}/annotations',
            data={
                'origin': 'other_origin',
                'data': {
                    'offset_from_host_galaxy': 1.5,
                    'some_boolean': True,
                },
                'group_ids': [public_group.id],
            },
            token=annotation_token,
        )
        assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/sources")

    # Filter for origin
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    alias_field = driver.wait_for_xpath(
        "//*[@data-testid='origin-text']//input",
    )
    alias_field.send_keys(origin)
    driver.click_xpath(
        "//button[text()='Submit']",
        scroll_parent=True,
    )

    # click the download button
    driver.click_xpath('//button[@aria-label="Download CSV"]')

    driver.wait_for_xpath('//*[contains(., "Downloading 20 sources")]')

    driver.wait_for_xpath_to_disappear('//*[contains(., "Downloading 20 sources")]')

    # check that the download has the right number of lines
    fpath = str(os.path.abspath(pjoin(cfg['paths.downloads_folder'], 'sources.csv')))
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 5:
        try_count += 1
        time.sleep(1)
    assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        assert len(lines.split('\n')) == 21
        assert lines.split('\n')[1].find("kowalski;other_origin") != -1
        assert lines.split('\n')[1].find("offset_from_host_galaxy;some_boolean") != -1
    finally:
        os.remove(fpath)


@pytest.mark.flaky(reruns=2)
def test_upload_download_comment_attachment(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    enter_comment_text(driver, comment_text)
    # attachment_file = driver.find_element_by_css_selector('input[type=file]')
    attachment_file = driver.wait_for_xpath(
        "//div[@data-testid='comments-accordion']//input[@name='attachment']"
    )

    filename = "spec.csv"
    attachment_file.send_keys(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            filename,
        ),
    )
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )
    try:
        comment_text_p = driver.wait_for_xpath(
            f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]',
            timeout=20,
        )
    except TimeoutException:
        driver.refresh()
        comment_text_p = driver.wait_for_xpath(
            f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]'
        )
    comment_div = comment_text_p.find_element(By.XPATH, "../..")
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()

    # Scroll up to top of comments list
    comments = driver.wait_for_xpath(
        "//div[@data-testid='comments-accordion']//p[text()='Comments']"
    )
    driver.scroll_to_element(comments)

    attachment_div = driver.wait_for_xpath(
        "//div[@data-testid='comments-accordion']//div[contains(text(), 'Attachment:')]"
    )
    attachment_button = driver.wait_for_xpath(
        '//div[@data-testid="comments-accordion"]//button[@data-testid="attachmentButton_spec"]'
    )

    # Try to open the preview dialog twice before failing to make it more robust
    try:
        ActionChains(driver).move_to_element(attachment_div).pause(0.5).perform()
        ActionChains(driver).move_to_element(attachment_button).pause(
            0.5
        ).click().perform()
        # Preview dialog
        driver.click_xpath('//a[@data-testid="attachmentDownloadButton_spec"]')
    except TimeoutException:
        ActionChains(driver).move_to_element(attachment_div).pause(0.5).perform()
        ActionChains(driver).move_to_element(attachment_button).pause(
            0.5
        ).click().perform()
        # Preview dialog
        driver.click_xpath('//a[@data-testid="attachmentDownloadButton_spec"]')

    fpath = str(os.path.abspath(pjoin(cfg['paths.downloads_folder'], 'spec.csv')))
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 3:
        try_count += 1
        assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        assert lines.split('\n')[0] == 'wavelengths,fluxes,instrument_id'
    finally:
        os.remove(fpath)


def test_gcn_summary_observations(
    driver,
    super_admin_user,
    super_admin_token,
    public_group,
):

    datafile = f'{os.path.dirname(__file__)}/../../../data/GW190814.xml'
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
            'galactic_latitude': 10,
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
        "showSources": True,
        "showGalaxies": False,
        "showObservations": False,
        "noText": False,
    }

    get_summary(driver, super_admin_user, public_group, False, False, True)

    fpath = str(
        os.path.abspath(
            pjoin(cfg['paths.downloads_folder'], 'Gcn Summary_2019-08-14T21 10 39.txt')
        )
    )
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 5:
        try_count += 1
        time.sleep(1)
    assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        data = lines.split('\n')
        assert "TITLE: GCN SUMMARY" in data[0]
        assert "SUBJECT: Follow-up" in data[1]
        assert "DATE" in data[2]
        assert (
            f"FROM:  {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
            in data[3]
        )
        assert f"on behalf of the {public_group.name}, report:" in data[5]

        assert any("Observations:" in line for line in data)
        assert any(
            'We observed the localization region of LVC trigger 2019-08-14T21:10:39.000 UTC'
            in line
            for line in data
        )
        assert any(
            "T-T0 (hr)" in line
            and "mjd" in line
            and "ra" in line
            and "dec" in line
            and "filter" in line
            and "exposure" in line
            and "limmag (ab)" in line
            for line in data
        )

    finally:
        os.remove(fpath)


def test_gcn_summary_galaxies(
    driver,
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
    event_data = {'xml': payload}

    dateobs = "2019-08-14T21:10:39"
    status, data = api('GET', f'gcn_event/{dateobs}', token=super_admin_token)

    if status == 404:
        status, data = api(
            'POST', 'gcn_event', data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data['status'] == 'success'

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
        "showSources": True,
        "showGalaxies": False,
        "showObservations": False,
        "noText": False,
    }

    get_summary(driver, super_admin_user, public_group, False, True, False)

    fpath = str(
        os.path.abspath(
            pjoin(cfg['paths.downloads_folder'], 'Gcn Summary_2019-08-14T21 10 39.txt')
        )
    )
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 5:
        try_count += 1
        time.sleep(1)
    assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        data = lines.split('\n')
        assert "TITLE: GCN SUMMARY" in data[0]
        assert "SUBJECT: Follow-up" in data[1]
        assert "DATE" in data[2]
        assert (
            f"FROM:  {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
            in data[3]
        )
        assert f"on behalf of the {public_group.name}, report:" in data[5]

        assert any(
            "Found 82 galaxies in the event's localization:" in line for line in data
        )
        assert any(
            "catalog" in line
            and "name" in line
            and "ra" in line
            and "dec" in line
            and "distmpc" in line
            and "redshift" in line
            for line in data
        )

    finally:
        os.remove(fpath)

    status, data = api(
        'DELETE', f'galaxy_catalog/{catalog_name}', token=super_admin_token
    )


def test_gcn_summary_sources(
    driver,
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

    datafile = f'{os.path.dirname(__file__)}/../../../data/GW190814.xml'
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
        "numberDetections": 1,
        "showSources": True,
        "showGalaxies": False,
        "showObservations": False,
        "noText": False,
    }

    get_summary(driver, super_admin_user, public_group, True, False, False)

    fpath = str(
        os.path.abspath(
            pjoin(cfg['paths.downloads_folder'], 'Gcn Summary_2019-08-14T21 10 39.txt')
        )
    )
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 5:
        try_count += 1
        time.sleep(1)
    assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        data = lines.split('\n')
        assert "TITLE: GCN SUMMARY" in data[0]
        assert "SUBJECT: Follow-up" in data[1]
        assert "DATE" in data[2]
        assert (
            f"FROM:  {super_admin_user.first_name} {super_admin_user.last_name} at ... <{super_admin_user.contact_email}>"
            in data[3]
        )
        assert f"on behalf of the {public_group.name}, report:" in data[5]

        assert any(
            "Found" in line and "in the event's localization" in line for line in data
        )
        assert any(
            "id" in line
            and "alias" in line
            and "ra" in line
            and "dec" in line
            and "redshift" in line
            for line in data
        )

        # source phot
        assert any("Photometry for source" in line for line in data)
        assert any(
            "mjd" in line and "mag±err (ab)" in line and "filter" in line
            for line in data
        )
    finally:
        os.remove(fpath)


def get_summary(driver, user, group, showSources, showGalaxies, showObservations):
    driver.get(f'/become_user/{user.id}')
    driver.get('/gcn_events/2019-08-14T21:10:39')

    summary_button = driver.wait_for_xpath_to_be_clickable(
        '//button[@name="gcn_summary"]'
    )
    driver.scroll_to_element_and_click(summary_button)

    group_select = '//*[@aria-labelledby="group-select"]'
    driver.wait_for_xpath(group_select)
    driver.click_xpath(group_select)
    group_select_option = f'//li[contains(., "{group.name}")]'
    driver.wait_for_xpath(group_select_option)
    driver.click_xpath(group_select_option)

    if showSources is True:
        show_sources = '//*[@label="Show Sources"]'
        driver.wait_for_xpath(show_sources)
        driver.click_xpath(show_sources, scroll_parent=True)
    if showGalaxies is True:
        show_galaxies = '//*[@label="Show Galaxies"]'
        driver.wait_for_xpath(show_galaxies)
        driver.click_xpath(show_galaxies, scroll_parent=True)
    if showObservations is True:
        show_observations = '//*[@label="Show Observations"]'
        driver.wait_for_xpath(show_observations)
        driver.click_xpath(show_observations, scroll_parent=True)

    get_summary_button = '//button[contains(.,"Generate")]'
    element = driver.wait_for_xpath(get_summary_button)
    element.send_keys(Keys.END)
    driver.click_xpath(get_summary_button, scroll_parent=True)

    retrieve_button = '//button[contains(.,"Retrieve")]'
    element = driver.wait_for_xpath(retrieve_button)
    element.send_keys(Keys.END)
    driver.click_xpath(retrieve_button, scroll_parent=True)

    text_area = '//textarea[@id="text"]'
    driver.wait_for_xpath(text_area, timeout=60)
    driver.wait_for_xpath('//textarea[contains(.,"TITLE: GCN SUMMARY")]', 60)

    download_button = '//button[contains(.,"Download")]'
    driver.click_xpath(download_button, scroll_parent=True)


def test_download_localization(super_admin_token):

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

    # wait for event to load
    for n_times in range(26):
        status, data = api('GET', f"gcn_event/{dateobs}", token=super_admin_token)
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 25

    skymap = 'LALInference.v1.fits.gz'
    assert data["data"]["dateobs"] == dateobs
    assert any(
        [loc['localization_name'] == skymap for loc in data["data"]["localizations"]]
    )

    status, data = api(
        'GET',
        f'localization/{dateobs}/name/{skymap}/download',
        token=super_admin_token,
    )
    assert status == 200
