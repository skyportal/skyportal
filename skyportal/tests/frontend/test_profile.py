import pytest
import uuid

from skyportal.tests import api
from tdtax import taxonomy, __version__
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


def test_token_acls_options_rendering1(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    driver.wait_for_xpath('//*[@data-testid="acls[0]"]')
    driver.wait_for_xpath('//*[@data-testid="acls[1]"]')
    driver.wait_for_xpath('//*[@data-testid="acls[2]"]')
    driver.wait_for_xpath('//*[@data-testid="acls[3]"]')
    driver.wait_for_xpath('//*[@data-testid="acls[4]"]')
    driver.wait_for_xpath_to_disappear('//*[@data-testid="acls[5]"]')


def test_token_acls_options_rendering2(driver, super_admin_user):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/profile")
    for i in range(5):
        driver.wait_for_xpath(f'//*[@data-testid="acls[{i}]"]')


@pytest.mark.xfail(strict=False)
def test_add_and_see_realname_in_user_profile(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    first_name_entry = driver.wait_for_xpath('//input[@name="firstName"]')
    first_name = str(uuid.uuid4())
    first_name_entry.send_keys(first_name)
    last_name_entry = driver.wait_for_xpath('//input[@name="lastName"]')
    last_name = str(uuid.uuid4())
    last_name_entry.send_keys(last_name)

    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@id="updateProfileButton"]')
    )

    # now that we added the name, let's see if it's displayed correctly
    name_display = driver.wait_for_xpath(
        '//*[@id="userRealname"][contains(@style, "visibility: visible")]'
    ).text
    assert name_display == f"{first_name} {last_name}"


def test_add_data_to_user_profile(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    first_name_entry = driver.wait_for_xpath('//input[@name="firstName"]')
    driver.scroll_to_element_and_click(first_name_entry)
    first_name = str(uuid.uuid4())
    first_name_entry.send_keys(first_name)
    last_name_entry = driver.wait_for_xpath('//input[@name="lastName"]')
    driver.scroll_to_element_and_click(last_name_entry)
    last_name = str(uuid.uuid4())
    last_name_entry.send_keys(last_name)

    email_entry = driver.wait_for_xpath('//input[@name="email"]')
    driver.scroll_to_element_and_click(email_entry)
    email = f"{str(uuid.uuid4())[:5]}@hotmail.com"
    email_entry.clear()
    email_entry.send_keys(email)

    phone_entry = driver.wait_for_xpath('//input[@name="phone"]')
    phone = "+12128675309"
    driver.scroll_to_element_and_click(phone_entry)
    phone_entry.send_keys(phone)

    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@id="updateProfileButton"]')
    )


def test_insufficient_name_entry_in_profile(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    first_name_entry = driver.wait_for_xpath('//input[@name="firstName"]')
    driver.scroll_to_element_and_click(first_name_entry)
    first_name_entry.clear()
    last_name_entry = driver.wait_for_xpath('//input[@name="lastName"]')
    last_name = str(uuid.uuid4())
    driver.scroll_to_element_and_click(last_name_entry)
    last_name_entry.send_keys(last_name)

    driver.click_xpath('//*[@id="updateProfileButton"]')

    helper = driver.wait_for_xpath('//p[@id="firstName_id-helper-text"]')
    assert helper.text == "Required"


@pytest.mark.flaky(reruns=2)
def test_profile_dropdown(driver, user):
    test_add_data_to_user_profile(driver, user)

    # click on profile dropdown
    avatar_element = driver.wait_for_xpath("//span[contains(@data-testid, 'avatar')]")
    driver.scroll_to_element_and_click(avatar_element)

    # check dropdown contents
    driver.wait_for_xpath("//p[contains(@data-testid, 'firstLastName')]")
    driver.wait_for_xpath("//p[contains(@data-testid, 'username')]")
    driver.wait_for_xpath("//a[contains(@data-testid, 'signOutButton')]")


def test_add_classification_shortcut(driver, user, public_group, taxonomy_token):
    status, data = api(
        'POST',
        'taxonomy',
        data={
            'name': "test taxonomy" + str(uuid.uuid4()),
            'hierarchy': taxonomy,
            'group_ids': [public_group.id],
            'provenance': f"tdtax_{__version__}",
            'version': __version__,
            'isLatest': True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    classifications_entry = driver.wait_for_xpath('//div[@id="classifications-select"]')
    driver.scroll_to_element_and_click(classifications_entry)
    agn_option = driver.wait_for_xpath('//li[@data-value="AGN"]')
    driver.scroll_to_element_and_click(agn_option)
    driver.wait_for_xpath('//span[contains(text(), "AGN")]')
    am_cvn_option = driver.wait_for_xpath('//li[@data-value="AM CVn"]')
    driver.scroll_to_element_and_click(am_cvn_option)
    driver.wait_for_xpath('//span[contains(text(), "AM CVn")]')
    ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    shortcut_name = str(uuid.uuid4())
    shortcut_name_entry = driver.wait_for_xpath('//input[@name="shortcutName"]')
    driver.scroll_to_element_and_click(shortcut_name_entry)
    shortcut_name_entry.send_keys(shortcut_name)

    add_shortcut_button = driver.wait_for_xpath(
        '//button[@data-testid="addShortcutButton"]'
    )
    driver.scroll_to_element_and_click(add_shortcut_button)

    driver.wait_for_xpath(f'//span[contains(text(), "{shortcut_name}")]')
    return shortcut_name


def test_classification_shortcut(driver, user, public_group, taxonomy_token):
    shortcut_name = test_add_classification_shortcut(
        driver, user, public_group, taxonomy_token
    )
    driver.get("/candidates")
    shortcut_button = driver.wait_for_xpath(f'//button[@data-testid="{shortcut_name}"]')
    driver.scroll_to_element_and_click(shortcut_button)
    driver.wait_for_xpath('//span[contains(text(), "AGN")]')
    driver.wait_for_xpath('//span[contains(text(), "AM CVn")]')


def test_delete_classification_shortcut(driver, user, public_group, taxonomy_token):
    shortcut_name = test_add_classification_shortcut(
        driver, user, public_group, taxonomy_token
    )
    delete_icon = driver.wait_for_xpath(
        '//*[@class="MuiSvgIcon-root MuiChip-deleteIcon"]'
    )
    driver.scroll_to_element_and_click(delete_icon)
    driver.wait_for_xpath_to_disappear(f'//span[contains(text(), "{shortcut_name}")]')
