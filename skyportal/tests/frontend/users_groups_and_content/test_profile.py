import time
import uuid

import numpy as np
import pytest
from playwright.sync_api import expect
from tdtax import __version__, taxonomy

from skyportal.tests import api


def test_token_acls_options_rendering1(page, user):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    for i in range(6):
        expect(page.locator(f'//*[@data-testid="acls[{i}]"]').first).to_be_visible()
    expect(page.locator('//*[@data-testid="acls[6]"]').first).to_be_hidden()


def test_token_acls_options_rendering2(page, super_admin_user):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/profile")
    for i in range(6):
        expect(page.locator(f'//*[@data-testid="acls[{i}]"]').first).to_be_visible()


def test_add_and_see_realname_in_user_profile(page, user):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    time.sleep(2)  # give it enough time to load the current profile

    first_name = str(uuid.uuid4())
    page.locator('//input[@name="firstName"]').first.fill(first_name)
    last_name = str(uuid.uuid4())
    page.locator('//input[@name="lastName"]').first.fill(last_name)

    page.locator('//*[@id="updateProfileButton"]').first.click()

    expect(
        page.locator(
            '//*[@id="userRealname"][contains(@style, "visibility: visible")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//*[@id="userRealname"][contains(text(), "{first_name}") and contains(text(), "{last_name}")]'
        ).first
    ).to_be_visible()


def test_add_and_see_affiliations_in_user_profile(page, user):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    time.sleep(1)

    affiliations_entry = page.locator('//input[@name="affiliations"]').first
    affiliation_1 = str(uuid.uuid4())
    affiliations_entry.fill(affiliation_1)
    affiliations_entry.press("Enter")
    affiliation_2 = str(uuid.uuid4())
    affiliations_entry.fill(affiliation_2)
    affiliations_entry.press("Enter")

    page.locator('//*[@id="updateProfileButton"]').first.click()

    expect(
        page.locator(
            '//*[@id="userAffiliations"][contains(@style, "visibility: visible")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//*[@id="userAffiliations"]/em[contains(text(), "{affiliation_1}") and contains(text(), "{affiliation_2}")]'
        ).first
    ).to_be_visible()


def test_add_data_to_user_profile(page, user):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    time.sleep(1)

    first_name = str(uuid.uuid4())
    page.locator('//input[@name="firstName"]').first.fill(first_name)
    last_name = str(uuid.uuid4())
    page.locator('//input[@name="lastName"]').first.fill(last_name)

    affiliations_entry = page.locator('//input[@name="affiliations"]').first
    affiliation = str(uuid.uuid4())
    affiliations_entry.fill(affiliation)
    affiliations_entry.press("Enter")

    email = f"{str(uuid.uuid4())[:5]}@hotmail.com"
    page.locator('//input[@name="email"]').first.fill(email)

    phone = "+12128675309"
    page.locator('//input[@name="phone"]').first.fill(phone)

    page.locator('//*[@id="updateProfileButton"]').first.click()


@pytest.mark.flaky(reruns=3)
def test_insufficient_name_entry_in_profile(page, user):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    time.sleep(1)

    page.locator('//input[@name="firstName"]').first.fill("")
    last_name = str(uuid.uuid4())
    page.locator('//input[@name="lastName"]').first.fill(last_name)

    page.locator('//*[@id="updateProfileButton"]').first.click()

    expect(page.locator('//p[@id="firstName_id-helper-text"]').first).to_have_text(
        "Required"
    )


@pytest.mark.flaky(reruns=2)
def test_profile_dropdown(page, user):
    test_add_data_to_user_profile(page, user)

    page.locator("//span[contains(@data-testid, 'avatar')]").first.click()

    expect(
        page.locator("//p[contains(@data-testid, 'firstLastName')]").first
    ).to_be_visible()
    expect(
        page.locator("//p[contains(@data-testid, 'username')]").first
    ).to_be_visible()
    expect(
        page.locator("//a[contains(@data-testid, 'signOutButton')]").first
    ).to_be_visible()


def test_join_auto_join_stream(page, user, super_admin_token):
    # Create a public (auto-join) stream
    stream_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "streams",
        data={"name": stream_name, "auto_join": True},
        token=super_admin_token,
    )
    assert status == 200
    stream_id = data["data"]["id"]

    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")

    join_button = page.locator(f'//*[@data-testid="joinStreamButton{stream_id}"]').first
    expect(join_button).to_be_visible()
    join_button.click()

    # After joining, the stream drops out of the "streams you can join" list
    expect(
        page.locator(f'//*[@data-testid="joinStreamButton{stream_id}"]').first
    ).to_be_hidden()


def add_classification_shortcut(page, user, public_group, taxonomy_token):
    status, _ = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    time.sleep(2)  # let the profile load and the taxonomies hydrate

    page.locator('//div[@id="classifications-select"]').first.click()
    page.locator('//li[@data-value="AGN"]').first.click()
    expect(page.locator('//span[contains(text(), "AGN")]').first).to_be_visible()
    page.locator('//li[@data-value="AM CVn"]').first.click()
    expect(page.locator('//span[contains(text(), "AM CVn")]').first).to_be_visible()
    page.keyboard.press("Escape")

    shortcut_name = str(uuid.uuid4())
    page.locator('//input[@name="shortcutName"]').first.fill(shortcut_name)

    page.locator('//button[@data-testid="addShortcutButton"]').first.click()
    expect(
        page.locator(f'//span[contains(text(), "{shortcut_name}")]').first
    ).to_be_visible()
    return shortcut_name


@pytest.mark.flaky(reruns=2)
def test_classification_shortcut(page, user, public_group, taxonomy_token):
    shortcut_name = add_classification_shortcut(
        page, user, public_group, taxonomy_token
    )
    page.goto("/candidates")
    page.locator(f'//button[@data-testid="{shortcut_name}"]').first.click()
    expect(page.locator('//span[contains(text(), "AGN")]').first).to_be_visible()
    expect(page.locator('//span[contains(text(), "AM CVn")]').first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_delete_classification_shortcut(page, user, public_group, taxonomy_token):
    shortcut_name = add_classification_shortcut(
        page, user, public_group, taxonomy_token
    )
    page.locator('//*[contains(@class,"MuiChip-deleteIcon")]').first.click()
    expect(
        page.locator(f'//span[contains(text(), "{shortcut_name}")]').first
    ).to_be_hidden()


@pytest.mark.skip(reason="Filtering on the origin has been disabled temporarily")
def test_set_automatically_visible_photometry(
    page, user, upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [59408, 59409, 59410],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "Muphoten", "lol"],
            "group_ids": [public_group.id],
            "altdata": [{"key1": "value1"}, {"key2": "value2"}, {"key3": "value3"}],
        },
        token=upload_data_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["ids"]) == 3

    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    page.locator(
        '//div[@id="filterSelectAutomaticallyVisiblePhotometry"]'
    ).first.click()
    page.locator('//li[@data-value="2massh"]').first.click()
    page.keyboard.press("Escape")

    page.locator(
        '//div[@id="originSelectAutomaticallyVisiblePhotometry"]'
    ).first.click()
    page.locator('//li[@data-value="Muphoten"]').first.click()
    page.keyboard.press("Escape")

    status, data = api("GET", "internal/profile", token=upload_data_token)
    assert status == 200
    assert data["data"]["preferences"]["automaticallyVisibleFilters"] == ["2massh"]
    assert data["data"]["preferences"]["automaticallyVisibleOrigins"] == ["Muphoten"]


@pytest.mark.skip(reason="Filtering on the origin has been disabled temporarily")
def test_photometry_buttons_form(
    page, user, upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [59408, 59409, 59410],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "Muphoten", "lol"],
            "group_ids": [public_group.id],
            "altdata": [{"key1": "value1"}, {"key2": "value2"}, {"key3": "value3"}],
        },
        token=upload_data_token,
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["ids"]) == 3

    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    page.locator('//div[@id="filterSelectPhotometryButtonsForm"]').first.click()
    page.locator('//li[@data-value="2massh"]').first.click()
    page.keyboard.press("Escape")

    page.locator('//div[@id="originSelectPhotometryButtonsForm"]').first.click()
    page.locator('//li[@data-value="Muphoten"]').first.click()
    page.keyboard.press("Escape")

    photometry_button_name = str(uuid.uuid4())
    page.locator('//input[@name="photometryButtonName"]').first.fill(
        photometry_button_name
    )

    page.locator('//button[@id="addPhotometryButtonButton"]').first.click()
    expect(
        page.locator(f'//span[contains(text(), "{photometry_button_name}")]').first
    ).to_be_visible()

    status, data = api("GET", "internal/profile", token=upload_data_token)
    assert status == 200
    assert data["data"]["preferences"]["photometryButtons"][photometry_button_name] == {
        "filters": ["2massh"],
        "origins": ["Muphoten"],
    }
