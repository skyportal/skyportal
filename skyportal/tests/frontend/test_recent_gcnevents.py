import os

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_recent_gcnevents(page, user, super_admin_token):
    datafile = f"{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    with open(datafile, "rb") as fid:
        payload = fid.read()
    data = {"xml": payload}

    status, data = api("POST", "gcn_event", data=data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{user.id}")
    page.goto("/")

    expect(page.locator('//*[text()="180116 00:36:53"]').first).to_be_visible()
    expect(page.locator('//*[text()="Fermi"]').first).to_be_visible()
    expect(page.locator('//*[text()="GRB"]').first).to_be_visible()
