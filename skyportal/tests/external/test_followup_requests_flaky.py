import glob
import os
import uuid

import pytest
import pandas as pd
import requests
from regions import Regions

from selenium.webdriver.common.action_chains import ActionChains
from baselayer.app.env import load_config
from skyportal.tests import api


cfg = load_config(config_files=["test_config.yaml"])
endpoint = cfg['app.sedm_endpoint']

sedm_isonline = False
try:
    requests.get(endpoint, timeout=5)
except requests.exceptions.ConnectTimeout:
    pass
else:
    sedm_isonline = True

if cfg['app.atlas.port'] is None:
    ATLAS_URL = f"{cfg['app.atlas.protocol']}://{cfg['app.atlas.host']}"
else:
    ATLAS_URL = (
        f"{cfg['app.atlas.protocol']}://{cfg['app.atlas.host']}:{cfg['app.atlas.port']}"
    )

atlas_isonline = False
try:
    requests.get(ATLAS_URL, timeout=5)
except requests.exceptions.ConnectTimeout:
    pass
else:
    atlas_isonline = True

PS1_URL = cfg['app.ps1_endpoint']

ps1_isonline = False
try:
    requests.get(PS1_URL, timeout=5)
except requests.exceptions.ConnectTimeout:
    pass
else:
    ps1_isonline = True

url = f"http://{cfg['app.lt_host']}:{cfg['app.lt_port']}/node_agent2/node_agent?wsdl"

lt_isonline = False
try:
    requests.get(url, timeout=5)
except requests.exceptions.ConnectTimeout:
    pass
else:
    lt_isonline = True

url = f"{cfg['app.lco_protocol']}://{cfg['app.lco_host']}:{cfg['app.lco_port']}/api/requestgroups/"
lco_isonline = False
try:
    requests.get(url, timeout=5)
except requests.exceptions.ConnectTimeout:
    pass
else:
    lco_isonline = True

if cfg['app.ztf.port'] is None:
    ZTF_URL = f"{cfg['app.ztf.protocol']}://{cfg['app.ztf.host']}"
else:
    ZTF_URL = f"{cfg['app.ztf.protocol']}://{cfg['app.ztf.host']}:{cfg['app.ztf.port']}"

ztf_isonline = False
try:
    requests.get(ZTF_URL, timeout=5)
except requests.exceptions.ConnectTimeout:
    pass
else:
    ztf_isonline = True

if cfg['app.kait.port'] is None:
    KAIT_URL = f"{cfg['app.kait.protocol']}://{cfg['app.kait.host']}"
else:
    KAIT_URL = (
        f"{cfg['app.kait.protocol']}://{cfg['app.kait.host']}:{cfg['app.kait.port']}"
    )

kait_isonline = False
try:
    requests.get(KAIT_URL, timeout=5)
except requests.exceptions.ConnectTimeout:
    pass
else:
    kait_isonline = True

swift_url = "https://www.swift.psu.edu/toop/submit_json.php"
swift_isonline = False
try:
    requests.get(swift_url, timeout=5)
except requests.exceptions.ConnectTimeout:
    pass
else:
    swift_isonline = True


def add_telescope_and_instrument(instrument_name, token):
    status, data = api("GET", f"instrument?name={instrument_name}", token=token)
    if len(data["data"]) == 1:
        if instrument_name == "ZTF":
            fielddatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Fields.csv'
            regionsdatafile = (
                f'{os.path.dirname(__file__)}/../../../data/ZTF_Region.reg'
            )

            fields = pd.read_csv(fielddatafile)
            fields = fields[698:701].to_dict(orient='list')

            field_data = {
                "field_data": fields,
                "field_region": Regions.read(regionsdatafile).serialize(format='ds9'),
            }

            status, updated_data = api(
                "PUT",
                f"instrument/{data['data'][0]['id']}",
                data=field_data,
                token=token,
            )
            assert status == 200
            assert updated_data["status"] == "success"
        return data["data"][0]

    telescope_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": telescope_name,
            "nickname": telescope_name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 10.0,
            "robotic": True,
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"
    telescope_id = data["data"]["id"]

    data = {
        "name": instrument_name,
        "type": "imager",
        "band": "Optical",
        "telescope_id": telescope_id,
        "filters": ["ztfg"],
        "api_classname": f"{instrument_name.upper()}API",
    }

    if instrument_name == "ZTF":
        fielddatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Fields.csv'
        regionsdatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Region.reg'

        fields = pd.read_csv(fielddatafile)
        fields = fields[698:701].to_dict(orient='list')

        data = {
            **data,
            "field_data": fields,
            "field_region": Regions.read(regionsdatafile).serialize(format='ds9'),
        }

    status, data = api(
        "POST",
        "instrument",
        data=data,
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"
    return data["data"]


def add_allocation_sedm(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"


def add_allocation_atlas(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
            "_altdata": '{"api_token": "testtoken"}',
            "types": ["forced_photometry"],
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"


def add_allocation_ps1(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
            "types": ["forced_photometry"],
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"


def add_allocation_lt(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
            "_altdata": '{"username": "fritz_bot", "password": "fX5uxZTDy3", "LT_proposalID": "GrowthTest"}',
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"


def add_allocation_slack(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
            '_altdata': '{"slack_workspace": "test_workspace", "slack_channel": "test_channel", "slack_token": "test_token"}',
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"


def add_allocation_lco(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
            "_altdata": '{"API_TOKEN": "testtoken", "PROPOSAL_ID": "TOM2020A-008"}',
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"


def add_allocation_ztf(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
            '_altdata': '{"access_token": "testtoken"}',
            "types": ["triggered", "forced_photometry"],
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"


def add_allocation_sedmv2(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
            '_altdata': '{"access_token": "testtoken"}',
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"


def add_allocation_uvotxrt(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
            '_altdata': '{"username": "anonymous", "secret": "anonymous"}',
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"
    return data["data"]


def add_allocation_kait(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"
    return data["data"]


def add_followup_request_using_frontend_and_verify_SEDMv2(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    idata = add_telescope_and_instrument("SEDMv2", super_admin_token)
    add_allocation_sedmv2(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "SEDMv2")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    # observation mode options
    options = driver.wait_for_xpath('//div[@id="root_observation_choice"]')
    driver.scroll_to_element_and_click(options)

    # click the IFU option
    driver.click_xpath('//li[@data-value="4"]')

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")
    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='SEDMv2-requests-header']")

    # look for the button to display more columns: data-testid="View Columns-iconButton"
    driver.click_xpath('//button[@data-testid="View Columns-iconButton"]')
    driver.click_xpath('//label/span[text()="exposure_time"]')

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "SEDMv2_followupRequestsTable")]//div[contains(., "IFU")]'
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SEDMv2_followupRequestsTable")]//div[contains(., "300")]'''
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SEDMv2_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


def add_followup_request_using_frontend_and_verify_KAIT(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    idata = add_telescope_and_instrument("KAIT", super_admin_token)
    add_allocation_kait(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "KAIT")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    # U band option
    driver.click_xpath(
        '//input[@id="root_observation_choices-0"]', wait_clickable=False
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")
    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='KAIT-requests-header']")
    driver.wait_for_xpath(
        '//div[contains(@data-testid, "KAIT_followupRequestsTable")]//div[contains(., "U")]'
    )
    # it should fail, as we don't provide real allocation info
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "KAIT_followupRequestsTable")]//div[contains(., "failed to submit")]'''
    )


def add_followup_request_using_frontend_and_verify_UVOTXRT(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    idata = add_telescope_and_instrument("UVOTXRT", super_admin_token)
    add_allocation_uvotxrt(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "UVOTXRT")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    # observation mode options
    options = driver.wait_for_xpath('//div[@id="root_request_type"]')
    driver.scroll_to_element_and_click(options)

    # click the XRT/UVOT ToO option
    driver.click_xpath('//li[@data-value="1"]')

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='UVOTXRT-requests-header']")

    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "UVOTXRT_followupRequestsTable")]//div[contains(., "submitted")]'''
    )

    # look for the button to display more columns: data-testid="View Columns-iconButton"
    driver.click_xpath('//button[@data-testid="View Columns-iconButton"]')
    driver.click_xpath('//label/span[text()="exposure_time"]')
    driver.click_xpath('//label/span[text()="obs_type"]')
    driver.click_xpath('//label/span[text()="source_type"]')

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "UVOTXRT_followupRequestsTable")]//div[contains(., "Light Curve")]'
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "UVOTXRT_followupRequestsTable")]//div[contains(., "4000")]'''
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "UVOTXRT_followupRequestsTable")]//div[contains(., "Optical fast transient")]'''
    )


def add_followup_request_using_frontend_and_verify_ZTF(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    idata = add_telescope_and_instrument("ZTF", super_admin_token)
    add_allocation_ztf(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "ZTF")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='ZTF-requests-header']")

    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "ZTF_followupRequestsTable")]//div[contains(., "submitted")]'''
    )

    # look for the button to display more columns: data-testid="View Columns-iconButton"
    driver.click_xpath('//button[@data-testid="View Columns-iconButton"]')
    driver.click_xpath('//label/span[text()="exposure_time"]')
    driver.click_xpath('//label/span[text()="subprogram_name"]')

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "ZTF_followupRequestsTable")]//div[contains(., "GRB")]'
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "ZTF_followupRequestsTable")]//div[contains(., "300")]'''
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "ZTF_followupRequestsTable")]//div[contains(., "g,r,i")]'''
    )


def add_followup_request_using_frontend_and_verify_Floyds(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("Floyds", super_admin_token)
    add_allocation_lco(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "Floyds")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    driver.scroll_to_element_and_click(submit_button, timeout=30)

    driver.click_xpath(
        "//div[@data-testid='Floyds-requests-header']", scroll_parent=True
    )

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "Floyds_followupRequestsTable")]//div[contains(., "submitted")]'
    )

    # look for the button to display more columns: data-testid="View Columns-iconButton"
    driver.click_xpath('//button[@data-testid="View Columns-iconButton"]')
    driver.click_xpath('//label/span[text()="exposure_time"]')
    driver.click_xpath('//label/span[text()="minimum_lunar_distance"]')

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "Floyds_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath(
        '//div[contains(@data-testid, "Floyds_followupRequestsTable")]//div[contains(., "30")]'
    )


def add_followup_request_using_frontend_and_verify_MUSCAT(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("MUSCAT", super_admin_token)
    add_allocation_lco(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "MUSCAT")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    driver.scroll_to_element_and_click(submit_button, timeout=30)

    driver.click_xpath("//div[@data-testid='MUSCAT-requests-header']")
    driver.wait_for_xpath(
        '//div[contains(@data-testid, "MUSCAT_followupRequestsTable")]//div[contains(., "submitted")]'
    )

    # look for the button to display more columns: data-testid="View Columns-iconButton"
    driver.click_xpath('//button[@data-testid="View Columns-iconButton"]')
    driver.click_xpath('//label/span[text()="exposure_time"]')
    driver.click_xpath('//label/span[text()="minimum_lunar_distance"]')

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "MUSCAT_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath(
        '//div[contains(@data-testid, "MUSCAT_followupRequestsTable")]//div[contains(., "30")]'
    )


def add_followup_request_using_frontend_and_verify_ATLAS(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("ATLAS", super_admin_token)
    add_allocation_atlas(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    # the MUI accordion is not expanded, we need to scroll to it and click
    header = driver.wait_for_xpath("//div[@id='forced-photometry-header']")
    driver.scroll_to_element_and_click(
        header,
        scroll_parent=True,
    )

    submit_button_xpath = (
        '//div[@data-testid="forced-photometry-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-forcedPhotometryAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "ATLAS")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    driver.scroll_to_element_and_click(submit_button, timeout=30)

    driver.click_xpath("//div[@data-testid='ATLAS-requests-header']")

    # submission should fail, as we don't provide real allocation info or endpoint
    driver.wait_for_xpath(
        '//div[contains(@data-testid, "ATLAS_followupRequestsTable")]//div[contains(., "failed to submit")]'
    )


def add_followup_request_using_frontend_and_verify_PS1(
    driver, super_admin_user, public_ZTFe028h94k, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("PS1", super_admin_token)
    add_allocation_ps1(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_ZTFe028h94k.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    # the MUI accordion is not expanded, we need to scroll to it and click
    header = driver.wait_for_xpath("//div[@id='forced-photometry-header']")
    driver.scroll_to_element_and_click(
        header,
        scroll_parent=True,
    )

    submit_button_xpath = (
        '//div[@data-testid="forced-photometry-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-forcedPhotometryAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "PS1")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    driver.scroll_to_element_and_click(submit_button, timeout=30)

    driver.click_xpath("//div[@data-testid='PS1-requests-header']")

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "PS1_followupRequestsTable")]//div[contains(., "submitted")]'
    )


def add_followup_request_using_frontend_and_verify_Spectral(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("Spectral", super_admin_token)
    add_allocation_lco(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for plots to load, if any
    driver.wait_for_xpath(
        '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]'
    )
    driver.wait_for_xpath(
        '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]'
    )

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "Spectral")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    # gp band option
    driver.click_xpath(
        '//input[@id="root_observation_choices-0"]', wait_clickable=False
    )

    # Y option
    driver.click_xpath(
        '//input[@id="root_observation_choices-4"]', wait_clickable=False
    )

    driver.scroll_to_element_and_click(submit_button, timeout=30)

    driver.click_xpath("//div[@data-testid='Spectral-requests-header']")

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "Spectral_followupRequestsTable")]//div[contains(., "submitted")]'
    )

    # look for the button to display more columns: data-testid="View Columns-iconButton"
    driver.click_xpath('//button[@data-testid="View Columns-iconButton"]')
    driver.click_xpath('//label/span[text()="exposure_time"]')
    driver.click_xpath('//label/span[text()="observation_choices"]')

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "Spectral_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath(
        '//div[contains(@data-testid, "Spectral_followupRequestsTable")]//div[contains(., "gp,Y")]'
    )


def add_followup_request_using_frontend_and_verify_Sinistro(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("Sinistro", super_admin_token)
    add_allocation_lco(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "Sinistro")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    # gp band option
    driver.click_xpath(
        '//input[@id="root_observation_choices-0"]', wait_clickable=False
    )

    # Y option
    driver.click_xpath(
        '//input[@id="root_observation_choices-4"]', wait_clickable=False
    )

    driver.scroll_to_element_and_click(submit_button, timeout=30)

    driver.click_xpath(
        "//div[@data-testid='Sinistro-requests-header']", scroll_parent=True
    )

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "Sinistro_followupRequestsTable")]//div[contains(., "submitted")]'
    )

    # look for the button to display more columns: data-testid="View Columns-iconButton"
    driver.click_xpath('//button[@data-testid="View Columns-iconButton"]')

    driver.click_xpath('//label/span[text()="exposure_time"]')
    driver.click_xpath('//label/span[text()="observation_choices"]')

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "Sinistro_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath(
        '//div[contains(@data-testid, "Sinistro_followupRequestsTable")]//div[contains(., "gp,Y")]'
    )


def add_followup_request_using_frontend_and_verify_SEDM(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    idata = add_telescope_and_instrument("SEDM", super_admin_token)
    add_allocation_sedm(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "SEDM")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    # mode select
    driver.click_xpath('//div[@id="root_observation_type"]', wait_clickable=False)

    # mix n match option
    driver.click_xpath('''//li[@data-value="5"]''')

    # u band option
    driver.click_xpath(
        '//input[@id="root_observation_choices-0"]', wait_clickable=False
    )

    # ifu option
    driver.click_xpath(
        '//input[@id="root_observation_choices-4"]', wait_clickable=False
    )

    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='SEDM-requests-header']")

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "Mix \'n Match")]'
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "u,IFU")]'''
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "1")]'''
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


def add_followup_request_using_frontend_and_verify_SPRAT(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("SPRAT", super_admin_token)
    add_allocation_lt(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = driver.wait_for_xpath(
        f'//li[contains(text(), "SPRAT")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        allocation,
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    driver.click_xpath('//input[@id="root_photometric"]', wait_clickable=False)

    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='SPRAT-requests-header']", timeout=30)

    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SPRAT_followupRequestsTable")]//div[contains(., "submitted")]''',
        timeout=20,
    )

    # look for the button to display more columns: data-testid="View Columns-iconButton"
    driver.click_xpath('//button[@data-testid="View Columns-iconButton"]')
    driver.click_xpath('//label/span[text()="observation_type"]')
    driver.click_xpath('//label/span[text()="exposure_time"]')

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "SPRAT_followupRequestsTable")]//div[contains(., "300")]',
        timeout=20,
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SPRAT_followupRequestsTable")]//div[contains(., "blue")]''',
        timeout=20,
    )


def add_followup_request_using_frontend_and_verify_IOI(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("IOI", super_admin_token)
    add_allocation_lt(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = (
        f"//li[contains(text(), 'IOI')][contains(text(), '{public_group.name}')]"
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(allocation),
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    # H band option
    driver.click_xpath(
        '//input[@id="root_observation_choices-0"]', wait_clickable=False
    )
    driver.click_xpath('//input[@id="root_photometric"]', wait_clickable=False)

    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='IOI-requests-header']", timeout=30)

    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "IOI_followupRequestsTable")]//div[contains(., "submitted")]''',
        timeout=20,
    )

    # look for the button to display more columns: data-testid="View Columns-iconButton"
    driver.click_xpath('//button[@data-testid="View Columns-iconButton"]')
    driver.click_xpath('//label/span[text()="exposure_time"]')
    driver.click_xpath('//label/span[text()="observation_choices"]')

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "IOI_followupRequestsTable")]//div[contains(., "300")]',
        timeout=20,
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "IOI_followupRequestsTable")]//div[contains(., "H")]''',
        timeout=20,
    )


def add_followup_request_using_frontend_and_verify_SLACK(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    idata = add_telescope_and_instrument("SLACK", super_admin_token)
    add_allocation_slack(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = (
        f"//li[contains(text(), 'SLACK')][contains(text(), '{public_group.name}')]"
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(allocation),
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    # ZTF g-band option
    driver.click_xpath(
        '//input[@id="root_observation_choices-0"]', wait_clickable=False
    )

    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='SLACK-requests-header']", timeout=30)

    # we are not pointing to a real slack channel, so it should fail
    driver.wait_for_xpath(
        '''//div[contains(text(), "failed to submit")]''',
        timeout=20,
    )
    driver.wait_for_xpath(
        '''//div[contains(text(), "ztfg")]''',
        timeout=20,
    )


def add_followup_request_using_frontend_and_verify_IOO(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("IOO", super_admin_token)
    add_allocation_lt(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    driver.scroll_to_element_and_click(select_box)

    allocation = (
        f"//li[contains(text(), 'IOO')][contains(text(), '{public_group.name}')]"
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(allocation),
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    # u band option
    driver.click_xpath(
        '//input[@id="root_observation_choices-0"]', wait_clickable=False
    )

    # z option
    driver.click_xpath(
        '//input[@id="root_observation_choices-4"]', wait_clickable=False
    )

    driver.click_xpath('//input[@id="root_photometric"]', wait_clickable=False)

    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='IOO-requests-header']", timeout=30)

    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "IOO_followupRequestsTable")]//div[contains(., "submitted")]''',
        timeout=20,
    )

    # look for the button to display more columns: data-testid="View Columns-iconButton"
    driver.click_xpath('//button[@data-testid="View Columns-iconButton"]')
    driver.click_xpath('//label/span[text()="exposure_time"]')
    driver.click_xpath('//label/span[text()="observation_choices"]')

    driver.wait_for_xpath(
        '//div[contains(@data-testid, "IOO_followupRequestsTable")]//div[contains(., "300")]',
        timeout=20,
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "IOO_followupRequestsTable")]//div[contains(., "u,z")]''',
        timeout=20,
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not swift_isonline, reason="UVOT/XRT server down")
def test_submit_new_followup_request_UVOTXRT(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_UVOTXRT(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not kait_isonline, reason="KAIT server down")
def test_submit_new_followup_request_KAIT(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_KAIT(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
def test_submit_new_followup_request_SEDMv2(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_SEDMv2(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not ztf_isonline, reason="ZTF server down")
def test_submit_new_followup_request_ZTF(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_ZTF(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_submit_new_followup_request_SEDM(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_SEDM(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lt_isonline, reason="LT server down")
def test_submit_new_followup_request_IOO(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_IOO(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lt_isonline, reason="LT server down")
def test_submit_new_followup_request_IOI(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_IOI(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lt_isonline, reason="LT server down")
def test_submit_new_followup_request_SPRAT(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_SPRAT(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
def test_submit_new_followup_request_SLACK(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SLACK(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_submit_new_followup_request_Sinistro(
    driver, super_admin_user, public_ZTF21aaeyldq, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_Sinistro(
        driver, super_admin_user, public_ZTF21aaeyldq, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_submit_new_followup_request_Spectral(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_Spectral(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not atlas_isonline, reason="ATLAS server down")
def test_submit_new_followup_request_ATLAS(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_ATLAS(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not ps1_isonline, reason="PS1 server down")
def test_submit_new_followup_request_PS1(
    driver, super_admin_user, public_ZTFe028h94k, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_PS1(
        driver, super_admin_user, public_ZTFe028h94k, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_submit_new_followup_request_MUSCAT(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_MUSCAT(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_submit_new_followup_request_Floyds(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_Floyds(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_edit_existing_followup_request(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SEDM(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )
    edit_button = driver.wait_for_xpath(
        '//button[contains(@data-testid, "editRequest")]'
    )
    driver.scroll_to_element_and_click(edit_button)
    mode_select = driver.wait_for_xpath(
        '//div[@role="dialog"]//div[@id="root_observation_type"]'
    )
    ActionChains(driver).move_to_element(mode_select).pause(1).click().perform()

    mix_n_match_option = driver.wait_for_xpath('''//li[@data-value="2"]''')
    driver.scroll_to_element_and_click(mix_n_match_option)

    submit_button = driver.wait_for_xpath(
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )

    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='SEDM-requests-header']")
    driver.wait_for_xpath(
        '//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "IFU")]'
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "1")]'''
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


def test_delete_followup_request_SEDMv2(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SEDMv2(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )

    driver.click_xpath(
        '//button[contains(@data-testid, "deleteRequest")]', scroll_parent=True
    )

    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "SEDMv2_followupRequestsTable")]//div[contains(., "IFU")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "SEDMv2_followupRequestsTable")]//div[contains(., "300")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "SEDMv2_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not ztf_isonline, reason='ZTF server down')
def test_delete_followup_request_ZTF(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_ZTF(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )

    driver.click_xpath(
        '//button[contains(@data-testid, "deleteRequest")]', scroll_parent=True
    )

    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "ZTF_followupRequestsTable")]//div[contains(., "GRB")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "ZTF_followupRequestsTable")]//div[contains(., "300")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "ZTF_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not sedm_isonline, reason='SEDM server down')
def test_delete_followup_request_SEDM(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SEDM(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )
    delete_button = driver.wait_for_xpath(
        '//button[contains(@data-testid, "deleteRequest")]'
    )
    driver.scroll_to_element_and_click(delete_button)

    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "u,IFU")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "1")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lt_isonline, reason="LT server down")
def test_delete_followup_request_IOO(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_IOO(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )

    driver.click_xpath(
        '//button[contains(@data-testid, "deleteRequest")]', scroll_parent=True
    )

    driver.wait_for_xpath_to_disappear(
        '//div[contains(@data-testid, "IOO_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "IOO_followupRequestsTable")]//div[contains(., "u,z")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "IOO_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lt_isonline, reason="LT server down")
def test_delete_followup_request_IOI(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_IOI(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )

    driver.click_xpath(
        '//button[contains(@data-testid, "deleteRequest")]', scroll_parent=True
    )

    driver.wait_for_xpath_to_disappear(
        '//div[contains(@data-testid, "IOI_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "IOI_followupRequestsTable")]//div[contains(., "H")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "IOI_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lt_isonline, reason="LT server down")
def test_delete_followup_request_SPRAT(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SPRAT(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )

    driver.click_xpath(
        '//button[contains(@data-testid, "deleteRequest")]', scroll_parent=True
    )

    driver.wait_for_xpath_to_disappear(
        '//div[contains(@data-testid, "SPRAT_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "SPRAT_followupRequestsTable")]//div[contains(., "blue")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "SPRAT_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_delete_followup_request_Sinistro(
    driver, super_admin_user, public_ZTF21aaeyldq, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_Sinistro(
        driver, super_admin_user, public_ZTF21aaeyldq, super_admin_token, public_group
    )

    driver.click_xpath(
        '//button[contains(@data-testid, "deleteRequest")]', scroll_parent=True
    )

    driver.wait_for_xpath_to_disappear(
        '//div[contains(@data-testid, "Sinistro_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "Sinistro_followupRequestsTable")]//div[contains(., "gp,Y")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "Sinistro_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_delete_followup_request_Spectral(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_Spectral(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )

    driver.click_xpath(
        '//button[contains(@data-testid, "deleteRequest")]', scroll_parent=True
    )

    driver.wait_for_xpath_to_disappear(
        '//div[contains(@data-testid, "Spectral_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "Spectral_followupRequestsTable")]//div[contains(., "gp,Y")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "Spectral_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_delete_followup_request_MUSCAT(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_MUSCAT(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )

    driver.click_xpath(
        '//button[contains(@data-testid, "deleteRequest")]', scroll_parent=True
    )

    driver.wait_for_xpath_to_disappear(
        '//div[contains(@data-testid, "MUSCAT_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "MUSCAT_followupRequestsTable")]//div[contains(., "30")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "MUSCAT_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_delete_followup_request_Floyds(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_Floyds(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )

    driver.click_xpath(
        '//button[contains(@data-testid, "deleteRequest")]', scroll_parent=True
    )

    driver.wait_for_xpath_to_disappear(
        '//div[contains(@data-testid, "Floyds_followupRequestsTable")]//div[contains(., "300")]'
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "Floyds_followupRequestsTable")]//div[contains(., "30")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//div[contains(@data-testid, "Floyds_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_submit_new_followup_request_two_groups(
    driver,
    super_admin_user,
    public_source_two_groups,
    super_admin_token,
    public_group,
    public_group2,
    view_only_token_group2,
):

    idata = add_telescope_and_instrument("SEDM", super_admin_token)
    add_allocation_sedm(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source_two_groups.id}")

    # wait for the plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-container"]/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass
    try:
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-content"]/div/div/div/div/div[@class=" bk-root"]',
            timeout=10,
        )
    except Exception:
        pass

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.wait_for_xpath(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    )
    select_box.click()

    allocation = (
        f'//li[contains(text(), "SEDM")][contains(text(), "{public_group.name}")]'
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(allocation),
        scroll_parent=True,
    )

    # Click somewhere definitely outside the select list to remove focus from select
    driver.click_xpath("//header")

    driver.click_xpath('//*[@id="selectGroups"]', wait_clickable=False)

    group1 = f'//*[@data-testid="group_{public_group.id}"]'
    driver.click_xpath(group1, scroll_parent=True, wait_clickable=False)

    group2 = f'//*[@data-testid="group_{public_group2.id}"]'
    driver.click_xpath(group2, scroll_parent=True, wait_clickable=False)

    # Click somewhere definitely outside the select list to remove focus from select
    # The manual ActionChains click seems to close the really long select list of groups
    # and then the second click actually takes the focus away.
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()
    driver.click_xpath("//header")

    # mode select
    driver.click_xpath('//div[@id="root_observation_type"]', wait_clickable=False)

    # mix n match option
    driver.click_xpath('''//li[@data-value="5"]''', scroll_parent=True)

    # u band option
    driver.click_xpath(
        '//input[@id="root_observation_choices-0"]', wait_clickable=False
    )

    # ifu option
    driver.click_xpath(
        '//input[@id="root_observation_choices-4"]', wait_clickable=False
    )
    driver.scroll_to_element_and_click(submit_button)

    driver.click_xpath("//div[@data-testid='SEDM-requests-header']", timeout=30)
    driver.wait_for_xpath(
        '//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "Mix \'n Match")]'
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "u,IFU")]'''
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "1")]'''
    )
    driver.wait_for_xpath(
        '''//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "submitted")]'''
    )

    filename = glob.glob(
        f'{os.path.dirname(__file__)}/../data/ZTF20abwdwoa_20200902_P60_v1.ascii'
    )[0]
    with open(filename) as f:
        ascii = f.read()

    status, data = api(
        'GET', f'sources/{public_source_two_groups.id}', token=super_admin_token
    )

    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        "POST",
        'spectrum/ascii',
        data={
            'obj_id': str(public_source_two_groups.id),
            'observed_at': '2020-01-01T00:00:00',
            'instrument_id': idata['id'],
            'fluxerr_column': 2,
            'followup_request_id': data['data']['followup_requests'][0]['id'],
            'ascii': ascii,
            'filename': os.path.basename(filename),
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data['status'] == 'success'

    sid = data['data']['id']
    status, data = api('GET', f'spectrum/{sid}', token=view_only_token_group2)

    assert status == 200
    assert data['status'] == 'success'
