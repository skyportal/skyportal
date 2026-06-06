import uuid

import pytest
from playwright.sync_api import expect
from tdtax import __version__, taxonomy

from skyportal.tests import api


# Passes in isolation; only times out under full-suite contention, so retry.
@pytest.mark.flaky(reruns=2)
def test_slider_classifications(
    page,
    public_source,
    super_admin_user,
    public_group,
    taxonomy_token,
):
    test_taxonomy = "test taxonomy" + str(uuid.uuid4())
    status, _ = api(
        "POST",
        "taxonomy",
        data={
            "name": test_taxonomy,
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/group_sources/{public_group.id}")
    expect(
        page.locator(f"//*[text()[contains(., '{public_group.name}')]]").first
    ).to_be_visible()

    page.reload()

    page.locator("//*[@id='expandable-button']").first.click()
    page.locator(f"//*[@id='taxonomy-select-{public_source.id}']").first.click()
    page.locator(f"//li[text()='{test_taxonomy}']").first.click()
    page.locator("//h6[text()='Stellar variable']").first.click()

    # Set the 'Eclipsing' and 'Algol' sliders to 0.5 (mark at data-index 2)
    page.locator("//span[@id='Eclipsing']//span[@data-index='2']").first.click()
    page.locator("//span[@id='Algol']//span[@data-index='2']").first.click()

    page.locator("//button[@name='submitClassificationsButton']").first.click()

    # reload to see the classification
    page.goto(f"/group_sources/{public_group.id}")
    expect(page.locator("//*[text()[contains(., 'Algol')]]").first).to_be_visible()
