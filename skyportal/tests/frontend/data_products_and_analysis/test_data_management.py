import pytest
from playwright.sync_api import expect

from skyportal.tests import IS_CI_BUILD


def test_share_data(
    page,
    super_admin_user,
    super_admin_token,
    public_source,
    public_group,
    public_group2,
):
    if IS_CI_BUILD:
        pytest.xfail("Xfailing this test on CI builds.")
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")
    page.locator('//*[text()="Share data"]').first.click()
    expect(page.locator(f"//div[text()='{public_group.name}']").first).to_be_visible()

    expect(page.locator('//div[@data-rowindex="0"]').first).to_be_visible()
    page.locator('//div[@data-rowindex="0"]//input[@type="checkbox"]').first.click()
    page.locator('//*[@id="dataSharingFormGroupsSelect"]').first.click()
    page.locator(f'//li[text()="{public_group2.name}"]').first.click()
    page.locator('//*[text()="Submit"]').first.click()
    expect(page.locator('//*[text()="Data successfully shared"]').first).to_be_visible()

    groups_str = ", ".join([public_group.name, public_group2.name])
    groups_str_alt = ", ".join([public_group2.name, public_group.name])
    expect(
        page.locator(f"//div[text()='{groups_str}']")
        .or_(page.locator(f"//div[text()='{groups_str_alt}']"))
        .first
    ).to_be_visible()


def test_delete_spectrum(page, public_source):
    spectrum = public_source.spectra[0]
    page.goto(f"/become_user/{spectrum.owner_id}")
    page.goto(f"/share_data/{public_source.id}")

    delete_button_xpath = f"//*[@data-testid='delete-spectrum-button-{spectrum.id}']"
    # Playwright auto-scrolls the target into view before clicking.
    page.locator(delete_button_xpath).first.click()
    page.locator("//*[@data-testid='yes-delete']").first.click()

    expect(
        page.locator(
            '//*[@data-testid="spectrum-table"]//div[@data-rowindex="1"]'
        ).first
    ).to_be_hidden()
