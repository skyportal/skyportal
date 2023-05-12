import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

from skyportal.tests import IS_CI_BUILD


def test_share_data(
    driver,
    super_admin_user,
    super_admin_token,
    public_source,
    public_group,
    public_group2,
):
    if IS_CI_BUILD:
        pytest.xfail("Xfailing this test on CI builds.")
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath('//*[text()="Share data"]')
    driver.wait_for_xpath(f"//div[text()='{public_group.name}']", timeout=15)

    driver.wait_for_xpath(
        '//div[@data-testid="photometry-div"]//*[@data-testid="MUIDataTableBodyRow-0"]',
        timeout=10,
    )
    driver.click_xpath('//*[@id="MUIDataTableSelectCell-0"]', wait_clickable=False)
    driver.click_xpath('//*[@id="dataSharingFormGroupsSelect"]')
    driver.click_xpath(f'//li[text()="{public_group2.name}"]', scroll_parent=True)
    driver.click_xpath('//*[text()="Submit"]')
    driver.wait_for_xpath('//*[text()="Data successfully shared"]', timeout=15)
    groups_str = ", ".join([public_group.name, public_group2.name])
    try:
        driver.wait_for_xpath(f"//div[text()='{groups_str}']")
    except TimeoutException:
        groups_str = ", ".join([public_group2.name, public_group.name])
        driver.wait_for_xpath(f"//div[text()='{groups_str}']")


def test_delete_spectrum(driver, public_source):

    spectrum = public_source.spectra[0]
    driver.get(f"/become_user/{spectrum.owner_id}")
    driver.get(f"/share_data/{public_source.id}")

    delete = driver.wait_for_xpath(
        "//*[contains(@data-testid, 'delete-spectrum-button')]"
    )
    driver.execute_script("arguments[0].scrollIntoView();", delete)
    ActionChains(driver).move_to_element(delete).perform()
    driver.click_xpath("//*[contains(@data-testid, 'delete-spectrum-button')]")
    driver.click_xpath("//*[@data-testid='yes-delete']")

    driver.wait_for_xpath_to_disappear(
        '//*[@data-testid="spectrum-table"]//*[@data-testid="MUIDataTableBodyRow-1"]'
    )
