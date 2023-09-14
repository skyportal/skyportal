import time
import uuid

import numpy as np
import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from tdtax import __version__, taxonomy

from skyportal.tests import api


def test_token_acls_options_rendering1(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    for i in range(6):
        driver.wait_for_xpath(f'//*[@data-testid="acls[{i}]"]')
    driver.wait_for_xpath_to_disappear('//*[@data-testid="acls[6]"]')


def test_token_acls_options_rendering2(driver, super_admin_user):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/profile")
    for i in range(6):
        driver.wait_for_xpath(f'//*[@data-testid="acls[{i}]"]')


def test_add_and_see_realname_in_user_profile(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    # give it enough time to load the current profile
    time.sleep(2)

    first_name_entry = driver.wait_for_xpath('//input[@name="firstName"]')
    first_name = str(uuid.uuid4())
    first_name_entry.send_keys(first_name)
    last_name_entry = driver.wait_for_xpath('//input[@name="lastName"]')
    last_name = str(uuid.uuid4())
    last_name_entry.send_keys(last_name)

    driver.scroll_to_element_and_click(
        driver.find_element(By.XPATH, '//*[@id="updateProfileButton"]')
    )

    # now that we added the name, let's see if it's displayed correctly
    driver.wait_for_xpath(
        '//*[@id="userRealname"][contains(@style, "visibility: visible")]'
    )

    driver.wait_for_xpath(
        f'//*[@id="userRealname"][contains(text(), "{first_name}") and contains(text(), "{last_name}")]'
    )


def test_add_and_see_affiliations_in_user_profile(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")

    # give some time to load the current profile
    time.sleep(1)

    affiliations_entry = driver.wait_for_xpath('//input[@name="affiliations"]')
    driver.scroll_to_element_and_click(affiliations_entry)
    affiliation_1 = str(uuid.uuid4())
    affiliations_entry.send_keys(affiliation_1)
    affiliations_entry.send_keys(Keys.ENTER)

    affiliation_2 = str(uuid.uuid4())
    affiliations_entry.send_keys(affiliation_2)
    affiliations_entry.send_keys(Keys.ENTER)

    driver.scroll_to_element_and_click(
        driver.find_element(By.XPATH, '//*[@id="updateProfileButton"]')
    )

    # now that we added the affiliations, let's see if they are displayed correctly
    driver.wait_for_xpath(
        '//*[@id="userAffiliations"][contains(@style, "visibility: visible")]'
    )
    driver.wait_for_xpath(
        f'//*[@id="userAffiliations"]/em[contains(text(), "{affiliation_1}") and contains(text(), "{affiliation_2}")]'
    )


def test_add_data_to_user_profile(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")

    # give some time to load the current profile
    time.sleep(1)

    first_name_entry = driver.wait_for_xpath('//input[@name="firstName"]')
    driver.scroll_to_element_and_click(first_name_entry)
    first_name = str(uuid.uuid4())
    first_name_entry.send_keys(first_name)
    last_name_entry = driver.wait_for_xpath('//input[@name="lastName"]')
    driver.scroll_to_element_and_click(last_name_entry)
    last_name = str(uuid.uuid4())
    last_name_entry.send_keys(last_name)

    affiliations_entry = driver.wait_for_xpath('//input[@name="affiliations"]')
    driver.scroll_to_element_and_click(affiliations_entry)
    affiliation = str(uuid.uuid4())
    affiliations_entry.send_keys(affiliation)
    affiliations_entry.send_keys(Keys.ENTER)

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
        driver.find_element(By.XPATH, '//*[@id="updateProfileButton"]')
    )


def test_insufficient_name_entry_in_profile(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")

    # give some time to load the current profile
    time.sleep(1)

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
    delete_icon = driver.wait_for_xpath('//*[contains(@class,"MuiChip-deleteIcon")]')
    driver.scroll_to_element_and_click(delete_icon)
    driver.wait_for_xpath_to_disappear(f'//span[contains(text(), "{shortcut_name}")]')


@pytest.mark.skip(reason="Filtering on the origin has been disabled temporarily")
def test_set_automatically_visible_photometry(
    driver, user, upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'instrument_id': ztf_camera.id,
            "mjd": [59408, 59409, 59410],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "Muphoten", "lol"],
            'group_ids': [public_group.id],
            "altdata": [{"key1": "value1"}, {"key2": "value2"}, {"key3": "value3"}],
        },
        token=upload_data_token,
    )

    assert status == 200
    assert data['status'] == 'success'
    ids = data["data"]["ids"]
    assert len(ids) == 3

    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    filter_select = driver.wait_for_xpath(
        '//div[@id="filterSelectAutomaticallyVisiblePhotometry"]'
    )
    driver.scroll_to_element_and_click(filter_select)
    massh_option = driver.wait_for_xpath('//li[@data-value="2massh"]')
    driver.scroll_to_element_and_click(massh_option)
    # remove focus from open select menu
    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    origin_select = driver.wait_for_xpath(
        '//div[@id="originSelectAutomaticallyVisiblePhotometry"]'
    )
    driver.scroll_to_element_and_click(origin_select)
    muphoten_option = driver.wait_for_xpath('//li[@data-value="Muphoten"]')
    muphoten_option.location_once_scrolled_into_view
    muphoten_option.click()
    ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    status, data = api('GET', 'internal/profile', token=upload_data_token)
    assert status == 200
    assert data['data']['preferences']['automaticallyVisibleFilters'] == ['2massh']
    assert data['data']['preferences']['automaticallyVisibleOrigins'] == ['Muphoten']


@pytest.mark.skip(reason="Filtering on the origin has been disabled temporarily")
def test_photometry_buttons_form(
    driver, user, upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'instrument_id': ztf_camera.id,
            "mjd": [59408, 59409, 59410],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "Muphoten", "lol"],
            'group_ids': [public_group.id],
            "altdata": [{"key1": "value1"}, {"key2": "value2"}, {"key3": "value3"}],
        },
        token=upload_data_token,
    )

    assert status == 200
    assert data['status'] == 'success'
    ids = data["data"]["ids"]
    assert len(ids) == 3

    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    filter_select = driver.wait_for_xpath(
        '//div[@id="filterSelectPhotometryButtonsForm"]'
    )
    driver.scroll_to_element_and_click(filter_select)
    massh_option = driver.wait_for_xpath('//li[@data-value="2massh"]')
    driver.scroll_to_element_and_click(massh_option)
    # remove focus from open select menu
    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    origin_select = driver.wait_for_xpath(
        '//div[@id="originSelectPhotometryButtonsForm"]'
    )
    driver.scroll_to_element_and_click(origin_select)
    muphoten_option = driver.wait_for_xpath('//li[@data-value="Muphoten"]')
    muphoten_option.location_once_scrolled_into_view
    muphoten_option.click()
    ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    photometry_button_name = str(uuid.uuid4())
    photometry_button_name_entry = driver.wait_for_xpath(
        '//input[@name="photometryButtonName"]'
    )
    driver.scroll_to_element_and_click(photometry_button_name_entry)
    photometry_button_name_entry.send_keys(photometry_button_name)

    add_photometry_button_button = driver.wait_for_xpath(
        '//button[@id="addPhotometryButtonButton"]'
    )
    driver.scroll_to_element_and_click(add_photometry_button_button)
    driver.wait_for_xpath(f'//span[contains(text(), "{photometry_button_name}")]')

    status, data = api('GET', 'internal/profile', token=upload_data_token)
    assert status == 200
    assert data['data']['preferences']['photometryButtons'][photometry_button_name] == {
        'filters': ['2massh'],
        'origins': ['Muphoten'],
    }
