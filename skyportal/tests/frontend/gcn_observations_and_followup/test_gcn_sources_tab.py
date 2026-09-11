import os

from playwright.sync_api import expect

from skyportal.tests import api, wait_for_gcn_event


def test_sources_tab_owns_its_query(page, super_admin_user, super_admin_token):
    """The Sources tab carries the source query's own form.

    The fields that decide which sources come back -- the detection window,
    "Require detections", the minimum number of detections -- used to live on a
    separate Query Form tab, shared with the galaxy and observation queries and
    run through a "query list" of targets. They belong with the results they
    filter.
    """
    datafile = (
        f"{os.path.dirname(__file__)}/../../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
    )
    with open(datafile, "rb") as fid:
        payload = fid.read()

    dateobs = "2018-01-16T00:36:53"
    status, _ = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        status, _ = api(
            "POST", "gcn_event", data={"xml": payload}, token=super_admin_token
        )
        assert status == 200

    wait_for_gcn_event(dateobs, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/gcn_events/{dateobs}")

    page.locator('//button[contains(., "Sources")]').first.click()

    expect(page.locator('//*[@data-testid="gcn-sources-form"]').first).to_be_visible()
    expect(page.locator('//button[contains(., "Find sources")]').first).to_be_visible()

    # The filters that shape this query are here, not on another tab.
    expect(page.locator('//*[@id="root_requireDetections"]').first).to_be_visible()
    expect(page.locator('//*[@id="root_numberDetections"]').first).to_be_visible()

    # Nothing has been run yet, so say so rather than implying a fetch.
    expect(
        page.locator('//*[contains(text(), "Run the query to list sources")]').first
    ).to_be_visible()


def test_every_tab_carries_its_own_query(page, super_admin_user, super_admin_token):
    """There is no shared query form left, and no query-target list.

    Each of Sources, Galaxies and Observations now carries the form for its own
    query, so nothing has to be configured on one tab and read on another.
    """
    dateobs = "2018-01-16T00:36:53"
    status, _ = api("GET", f"gcn_event/{dateobs}", token=super_admin_token)
    if status == 404:
        datafile = (
            f"{os.path.dirname(__file__)}/../../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml"
        )
        with open(datafile, "rb") as fid:
            payload = fid.read()
        status, _ = api(
            "POST", "gcn_event", data={"xml": payload}, token=super_admin_token
        )
        assert status == 200
    wait_for_gcn_event(dateobs, super_admin_token)

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/gcn_events/{dateobs}")

    # The separate query-form tab, and the list of targets it ran, are gone.
    expect(page.locator('//button[normalize-space(.)="Query Form"]')).to_have_count(0)
    expect(
        page.locator('//button[normalize-space(.)="Observations Query"]')
    ).to_have_count(0)
    expect(page.locator('//*[@id="root_queryList"]')).to_have_count(0)

    # The localization applies to every tab, so it sits above them.
    expect(page.locator('//*[@id="localizationSelectLabel"]').first).to_be_visible()

    # Each query's own form lives with its results.
    page.locator('//button[normalize-space(.)="Observations"]').first.click()
    expect(page.locator('//*[@id="instrumentSelectLabel"]').first).to_be_visible()
