import glob
import os
import uuid

import pandas as pd
import pytest
import requests
from playwright.sync_api import expect
from regions import Regions

from baselayer.app.env import load_config
from skyportal.tests import api
from skyportal.tests.external.test_moving_objects import add_telescope_and_instrument

cfg = load_config(config_files=["test_config.yaml"])
endpoint = cfg["app.sedm_endpoint"]

sedm_isonline = False
try:
    requests.get(endpoint, timeout=5)
except requests.exceptions.RequestException:
    # Any connection error (timeout, refused, or an unconfigured/None endpoint)
    # just means the live SEDM service isn't reachable from the test runner.
    pass
else:
    sedm_isonline = True

if cfg["app.atlas.port"] is None:
    ATLAS_URL = f"{cfg['app.atlas.protocol']}://{cfg['app.atlas.host']}"
else:
    ATLAS_URL = (
        f"{cfg['app.atlas.protocol']}://{cfg['app.atlas.host']}:{cfg['app.atlas.port']}"
    )

atlas_isonline = False
try:
    requests.get(ATLAS_URL, timeout=5)
except requests.exceptions.RequestException:
    pass
else:
    atlas_isonline = True

PS1_URL = cfg["app.ps1_endpoint"]

ps1_isonline = False
try:
    requests.get(PS1_URL, timeout=5)
except requests.exceptions.ConnectTimeout:
    pass
else:
    ps1_isonline = True

url = f"{cfg['app.lco_protocol']}://{cfg['app.lco_host']}:{cfg['app.lco_port']}/api/requestgroups/"
lco_isonline = False
try:
    requests.get(url, timeout=5)
except requests.exceptions.ConnectTimeout:
    pass
else:
    lco_isonline = True

if cfg["app.ztf.port"] is None:
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

if cfg["app.kait.port"] is None:
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


def add_allocation_slack(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
            "_altdata": '{"slack_workspace": "test_workspace", "slack_channel": "test_channel", "slack_token": "test_token"}',
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
            "_altdata": '{"access_token": "testtoken"}',
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
            "_altdata": '{"access_token": "testtoken"}',
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
            "_altdata": '{"username": "anonymous", "secret": "anonymous"}',
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


def show_followup_columns(page, instrument_name, *columns):
    """Reveal hidden columns in an instrument's follow-up requests DataGrid.

    MUI X v8 replaced the old "View Columns" toolbar button with the shared
    DataGridToolbar's columns-panel trigger plus a checkbox per column keyed on
    its header name (the param name).
    """
    table = page.locator(
        f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]'
    ).first
    table.locator('[data-testid="datagrid-columns-button"]').first.click()
    for column in columns:
        page.get_by_role("checkbox", name=column, exact=True).check()
    page.keyboard.press("Escape")


def add_followup_request_using_frontend_and_verify_SEDMv2(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "SEDMv2", super_admin_token
    )
    add_allocation_sedmv2(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    # Click somewhere outside to remove focus from instrument select
    page.keyboard.press("Escape")

    # observation mode options
    options = page.locator('//div[@id="root_observation_choice"]').first
    options.click()

    # click the IFU option
    page.locator('//li[@data-value="4"]').first.click()

    # Click somewhere outside to remove focus from instrument select
    page.keyboard.press("Escape")
    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()
    show_followup_columns(page, instrument_name, "exposure_time")

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "IFU")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]"""
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_KAIT(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "KAIT", super_admin_token
    )
    add_allocation_kait(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    # Click somewhere outside to remove focus from instrument select
    page.keyboard.press("Escape")

    # U band option
    page.locator('//input[@id="root_observation_choices-0"]').first.click()

    # Click somewhere outside to remove focus from instrument select
    page.keyboard.press("Escape")
    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "U")]'
        ).first
    ).to_be_visible()
    # it should fail, as we don't provide real allocation info
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "failed to submit")]"""
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_UVOTXRT(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "UVOTXRT", super_admin_token
    )
    add_allocation_uvotxrt(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    # Click somewhere outside to remove focus from instrument select
    page.keyboard.press("Escape")

    # observation mode options
    options = page.locator('//div[@id="root_request_type"]').first
    options.click()

    # click the XRT/UVOT ToO option
    page.locator('//li[@data-value="1"]').first.click()

    # Click somewhere outside to remove focus from instrument select
    page.keyboard.press("Escape")

    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()

    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_visible()

    show_followup_columns(
        page, instrument_name, "exposure_time", "obs_type", "source_type"
    )

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "Light Curve")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "4000")]"""
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "Optical fast transient")]"""
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_ZTF(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "ZTF", super_admin_token, fields_ids=list(range(699, 704))
    )
    add_allocation_ztf(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    # Click somewhere outside to remove focus from instrument select
    page.keyboard.press("Escape")

    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()

    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_visible()

    show_followup_columns(page, instrument_name, "exposure_time", "subprogram_name")

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "GRB")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]"""
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "g,r,i")]"""
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_Floyds(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "Floyds", super_admin_token
    )
    add_allocation_lco(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]'
        ).first
    ).to_be_visible()

    show_followup_columns(
        page, instrument_name, "exposure_time", "minimum_lunar_distance"
    )

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "30")]'
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_MUSCAT(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "MUSCAT", super_admin_token
    )
    add_allocation_lco(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]'
        ).first
    ).to_be_visible()

    show_followup_columns(
        page, instrument_name, "exposure_time", "minimum_lunar_distance"
    )

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "30")]'
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_ATLAS(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "ATLAS", super_admin_token
    )
    add_allocation_atlas(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    # the MUI accordion is not expanded, we need to scroll to it and click
    header = page.locator("//div[@id='forced-photometry-header']").first
    header.click()

    submit_button_xpath = (
        '//div[@data-testid="forced-photometry-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-forcedPhotometryAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()

    # submission should fail, as we don't provide real allocation info or endpoint
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "failed to submit")]'
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_PS1(
    page, super_admin_user, public_ZTFe028h94k, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "PS1", super_admin_token
    )
    add_allocation_ps1(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_ZTFe028h94k.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    # the MUI accordion is not expanded, we need to scroll to it and click
    header = page.locator("//div[@id='forced-photometry-header']").first
    header.click()

    submit_button_xpath = (
        '//div[@data-testid="forced-photometry-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-forcedPhotometryAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]'
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_Spectral(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "Spectral", super_admin_token
    )
    add_allocation_lco(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    # gp band option
    page.locator('//input[@id="root_observation_choices-0"]').first.click()

    # Y option
    page.locator('//input[@id="root_observation_choices-4"]').first.click()

    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]'
        ).first
    ).to_be_visible()

    show_followup_columns(page, instrument_name, "exposure_time", "observation_choices")

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "gp,Y")]'
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_Sinistro(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "Sinistro", super_admin_token
    )
    add_allocation_lco(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    # gp band option
    page.locator('//input[@id="root_observation_choices-0"]').first.click()

    # Y option
    page.locator('//input[@id="root_observation_choices-4"]').first.click()

    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]'
        ).first
    ).to_be_visible()

    show_followup_columns(page, instrument_name, "exposure_time", "observation_choices")

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "gp,Y")]'
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_SEDM(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "SEDM", super_admin_token
    )
    add_allocation_sedm(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = page.locator(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    ).first
    allocation.click()

    # Click somewhere outside to remove focus from instrument select
    page.keyboard.press("Escape")

    # mode select
    page.locator('//div[@id="root_observation_type"]').first.click()

    # mix n match option
    page.locator("""//li[@data-value="5"]""").first.click()

    # u band option
    page.locator('//input[@id="root_observation_choices-0"]').first.click()

    # ifu option
    page.locator('//input[@id="root_observation_choices-4"]').first.click()

    submit_button.click()

    # page.locator(f"//*[@data-testid='SEDM-requests-header']").first.click()
    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "Mix \'n Match")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "u,IFU")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "1")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]'
        ).first
    ).to_be_visible()

    return instrument_id, instrument_name


def add_followup_request_using_frontend_and_verify_SLACK(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""
    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "SLACK", super_admin_token
    )
    add_allocation_slack(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = f"//li[contains(text(), '{instrument_name}')][contains(text(), '{public_group.name}')]"
    page.locator(allocation).first.click()

    # Click somewhere outside to remove focus from instrument select
    page.keyboard.press("Escape")

    # ZTF g-band option
    page.locator('//input[@id="root_observation_choices-0"]').first.click()

    submit_button.click()

    page.locator(f"//*[@data-testid='{instrument_name}-requests-header']").first.click()

    # we are not pointing to a real slack channel, so it should fail
    expect(
        page.locator("""//div[contains(text(), "failed to submit")]""").first
    ).to_be_visible()
    expect(page.locator("""//div[contains(text(), "ztfg")]""").first).to_be_visible()

    return instrument_id, instrument_name


@pytest.mark.skipif(not swift_isonline, reason="UVOT/XRT server down")
def test_submit_new_followup_request_UVOTXRT(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_UVOTXRT(
        page, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.skipif(not kait_isonline, reason="KAIT server down")
def test_submit_new_followup_request_KAIT(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_KAIT(
        page, super_admin_user, public_source, super_admin_token, public_group
    )


#
def test_submit_new_followup_request_SEDMv2(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SEDMv2(
        page, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.skipif(not ztf_isonline, reason="ZTF server down")
def test_submit_new_followup_request_ZTF(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_ZTF(
        page, super_admin_user, public_source, super_admin_token, public_group
    )


#
@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_submit_new_followup_request_SEDM(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SEDM(
        page, super_admin_user, public_source, super_admin_token, public_group
    )


def test_submit_new_followup_request_SLACK(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SLACK(
        page, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_submit_new_followup_request_Sinistro(
    page, super_admin_user, public_ZTF21aaeyldq, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_Sinistro(
        page, super_admin_user, public_ZTF21aaeyldq, super_admin_token, public_group
    )


@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_submit_new_followup_request_Spectral(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_Spectral(
        page, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.skipif(not atlas_isonline, reason="ATLAS server down")
def test_submit_new_followup_request_ATLAS(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_ATLAS(
        page, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.skipif(not ps1_isonline, reason="PS1 server down")
def test_submit_new_followup_request_PS1(
    page, super_admin_user, public_ZTFe028h94k, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_PS1(
        page, super_admin_user, public_ZTFe028h94k, super_admin_token, public_group
    )


@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_submit_new_followup_request_MUSCAT(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_MUSCAT(
        page, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_submit_new_followup_request_Floyds(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_Floyds(
        page, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_edit_existing_followup_request(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SEDM(
        page, super_admin_user, public_source, super_admin_token, public_group
    )
    edit_button = page.locator('//button[contains(@data-testid, "editRequest")]').first
    edit_button.click()
    mode_select = page.locator(
        '//div[@role="dialog"]//div[@id="root_observation_type"]'
    ).first
    mode_select.click()

    mix_n_match_option = page.locator("""//li[@data-value="2"]""").first
    mix_n_match_option.click()

    submit_button = page.locator(
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    ).first

    submit_button.click()

    page.locator("//*[@data-testid='SEDM-requests-header']").first.click()
    expect(
        page.locator(
            '//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "IFU")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            """//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "1")]"""
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            """//div[contains(@data-testid, "SEDM_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_visible()


def test_delete_followup_request_SEDMv2(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    _, instrument_name = add_followup_request_using_frontend_and_verify_SEDMv2(
        page, super_admin_user, public_source, super_admin_token, public_group
    )

    page.locator('//button[contains(@data-testid, "deleteRequest")]').first.click()

    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "IFU")]"""
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]"""
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_hidden()


@pytest.mark.skipif(not ztf_isonline, reason="ZTF server down")
def test_delete_followup_request_ZTF(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    _, instrument_name = add_followup_request_using_frontend_and_verify_ZTF(
        page, super_admin_user, public_source, super_admin_token, public_group
    )

    page.locator('//button[contains(@data-testid, "deleteRequest")]').first.click()

    expect(
        page.locator(
            """//div[contains(@data-testid, "ZTF_followupRequestsTable")]//div[contains(., "GRB")]"""
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            """//div[contains(@data-testid, "ZTF_followupRequestsTable")]//div[contains(., "300")]"""
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            """//div[contains(@data-testid, "ZTF_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_hidden()


@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_delete_followup_request_SEDM(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    _, instrument_name = add_followup_request_using_frontend_and_verify_SEDM(
        page, super_admin_user, public_source, super_admin_token, public_group
    )
    delete_button = page.locator(
        '//button[contains(@data-testid, "deleteRequest")]'
    ).first
    delete_button.click()

    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "u,IFU")]"""
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "1")]"""
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_hidden()


@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_delete_followup_request_Sinistro(
    page, super_admin_user, public_ZTF21aaeyldq, super_admin_token, public_group
):
    _, instrument_name = add_followup_request_using_frontend_and_verify_Sinistro(
        page, super_admin_user, public_ZTF21aaeyldq, super_admin_token, public_group
    )

    page.locator('//button[contains(@data-testid, "deleteRequest")]').first.click()

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]'
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "gp,Y")]"""
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_hidden()


@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_delete_followup_request_Spectral(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    _, instrument_name = add_followup_request_using_frontend_and_verify_Spectral(
        page, super_admin_user, public_source, super_admin_token, public_group
    )

    page.locator('//button[contains(@data-testid, "deleteRequest")]').first.click()

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]'
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "gp,Y")]"""
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_hidden()


@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_delete_followup_request_MUSCAT(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    _, instrument_name = add_followup_request_using_frontend_and_verify_MUSCAT(
        page, super_admin_user, public_source, super_admin_token, public_group
    )

    page.locator('//button[contains(@data-testid, "deleteRequest")]').first.click()

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]'
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "30")]"""
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_hidden()


@pytest.mark.skipif(not lco_isonline, reason="LCO server down")
def test_delete_followup_request_Floyds(
    page, super_admin_user, public_source, super_admin_token, public_group
):
    _, instrument_name = add_followup_request_using_frontend_and_verify_Floyds(
        page, super_admin_user, public_source, super_admin_token, public_group
    )

    page.locator('//button[contains(@data-testid, "deleteRequest")]').first.click()

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "300")]'
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "30")]"""
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_hidden()


@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_submit_new_followup_request_two_groups(
    page,
    super_admin_user,
    public_source_two_groups,
    super_admin_token,
    public_group,
    public_group2,
    view_only_token_group2,
):
    _, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "SEDM", super_admin_token
    )
    add_allocation_sedm(instrument_id, public_group.id, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")

    page.goto(f"/source/{public_source_two_groups.id}")

    # The form interactions below auto-wait; don't gate on the heavy Plotly
    # plots, which can take far longer to render and time the test out under load.

    submit_button_xpath = (
        '//div[@data-testid="followup-request-form"]//button[@type="submit"]'
    )
    submit_button = page.locator(submit_button_xpath).first

    select_box = page.locator(
        "//div[@id='mui-component-select-followupRequestAllocationSelect']"
    ).first
    select_box.click()

    allocation = f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]'
    page.locator(allocation).first.click()

    # Click somewhere definitely outside the select list to remove focus from select
    page.keyboard.press("Escape")

    page.locator('//*[@id="selectGroups"]').first.click()

    group1 = f'//*[@data-testid="group_{public_group.id}"]'
    page.locator(group1).first.click()

    group2 = f'//*[@data-testid="group_{public_group2.id}"]'
    page.locator(group2).first.click()

    # Close the really long select list of groups and take focus away from it.
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")

    # mode select
    page.locator('//div[@id="root_observation_type"]').first.click()

    # mix n match option
    page.locator("""//li[@data-value="5"]""").first.click()

    # u band option
    page.locator('//input[@id="root_observation_choices-0"]').first.click()

    # ifu option
    page.locator('//input[@id="root_observation_choices-4"]').first.click()
    submit_button.click()

    page.locator("//*[@data-testid='SEDM-requests-header']").first.click()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "Mix \'n Match")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "u,IFU")]"""
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "1")]"""
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"""//div[contains(@data-testid, "{instrument_name}_followupRequestsTable")]//div[contains(., "submitted")]"""
        ).first
    ).to_be_visible()

    filename = glob.glob(
        f"{os.path.dirname(__file__)}/../data/ZTF20abwdwoa_20200902_P60_v1.ascii"
    )[0]
    with open(filename) as f:
        ascii = f.read()

    status, data = api(
        "GET", f"sources/{public_source_two_groups.id}", token=super_admin_token
    )

    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "POST",
        "spectrum/ascii",
        data={
            "obj_id": str(public_source_two_groups.id),
            "observed_at": "2020-01-01T00:00:00",
            "instrument_id": instrument_id,
            "fluxerr_column": 2,
            "followup_request_id": data["data"]["followup_requests"][0]["id"],
            "ascii": ascii,
            "filename": os.path.basename(filename),
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"

    sid = data["data"]["id"]
    status, data = api("GET", f"spectrum/{sid}", token=view_only_token_group2)

    assert status == 200
    assert data["status"] == "success"
