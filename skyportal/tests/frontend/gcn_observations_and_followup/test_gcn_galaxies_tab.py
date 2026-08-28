import os

from playwright.sync_api import expect

from skyportal.tests import api, wait_for_gcn_event


def test_galaxies_tab_owns_its_query(page, super_admin_user, super_admin_token):
    """The Galaxies tab carries its own form and says when nothing has been run.

    It used to share one form with the Sources and Observations tabs, so the
    galaxy query could only be run by ticking "galaxies" in that form's query
    list, on a different tab, alongside fields (time range, detections) that
    the galaxy query never reads. Until then the tab claimed to be fetching.
    """
    datafile = (
        f"{os.path.dirname(__file__)}/../../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    )
    with open(datafile, "rb") as fid:
        payload = fid.read()

    dateobs = "2018-01-16T00:36:53"
    status, _ = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, data = api(
            "POST", "gcn_event", data={"xml": payload}, token=super_admin_token
        )
        assert status == 200

    wait_for_gcn_event(dateobs, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/gcn_events/{dateobs}")

    page.locator('//button[contains(., "Galaxies")]').first.click()

    # The tab has its own form, rather than sending the reader to another tab.
    expect(page.locator('//*[@data-testid="gcn-galaxies-form"]').first).to_be_visible()
    expect(page.locator('//button[contains(., "Find galaxies")]').first).to_be_visible()

    # Nothing has been asked for yet, so it must not claim to be fetching.
    expect(
        page.locator('//*[contains(text(), "Run the query to list galaxies")]').first
    ).to_be_visible()
    expect(page.locator('//*[contains(text(), "Fetching galaxies")]')).to_have_count(0)

    # The fields the galaxy query does not read are not on this form.
    expect(page.locator('//*[@id="root_requireDetections"]')).to_have_count(0)
    expect(page.locator('//*[@id="root_numberDetections"]')).to_have_count(0)
    expect(page.locator('//*[@id="root_queryList"]')).to_have_count(0)

    # Running it reports an answer rather than sitting on "fetching".
    page.locator('//button[contains(., "Find galaxies")]').first.click()
    expect(
        page.locator('//*[contains(text(), "Run the query to list galaxies")]')
    ).to_have_count(0)
