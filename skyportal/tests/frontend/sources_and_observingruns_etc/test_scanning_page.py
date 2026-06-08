import time
import uuid

import pytest
from playwright.sync_api import expect
from tdtax import __version__, taxonomy

from skyportal.tests import api

from ....utils.naive_datetime import utcnow_naive


@pytest.mark.flaky(reruns=2)
def test_candidate_group_filtering(
    page,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    super_admin_token,
):
    candidate_id = str(uuid.uuid4())
    for i in range(5):
        status, data = api(
            "POST",
            "candidates",
            data={
                "id": f"{candidate_id}_{i}",
                "ra": 234.22,
                "dec": -22.33,
                "redshift": 3,
                "altdata": {"simbad": {"class": "RRLyr"}},
                "transient": False,
                "ra_dis": 2.3,
                "passed_at": str(utcnow_naive()),
                "filter_ids": [public_filter.id],
            },
            token=upload_data_token,
        )
        assert status == 200

    status, data = api(
        "POST",
        "groups",
        data={"name": str(uuid.uuid4()), "group_admins": [user.id]},
        token=super_admin_token,
    )
    new_group_id = data["data"]["id"]
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/candidates")
    group_checkbox = page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first
    group_checkbox.click()
    submit_button = page.locator('//button[text()="Search"]').first
    submit_button.click()

    expect(
        page.locator('//*[contains(., "Found 6 candidates.")]').first
    ).to_be_visible()

    group_checkbox.click()
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{new_group_id}"]'
    ).first.click()
    submit_button.click()

    expect(
        page.locator('//*[contains(., "Found 0 candidates.")]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_candidate_saved_status_filtering(
    page,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    manage_groups_token,
):
    candidate_id = str(uuid.uuid4())
    for i in range(5):
        status, data = api(
            "POST",
            "sources",
            data={
                "id": f"{candidate_id}_{i}",
                "ra": 234.22,
                "dec": -22.33,
                "redshift": 3,
                "altdata": {"simbad": {"class": "RRLyr"}},
                "transient": False,
                "ra_dis": 2.3,
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200
        status, data = api(
            "POST",
            "candidates",
            data={
                "id": f"{candidate_id}_{i}",
                "ra": 234.22,
                "dec": -22.33,
                "redshift": 3,
                "altdata": {"simbad": {"class": "RRLyr"}},
                "transient": False,
                "ra_dis": 2.3,
                "filter_ids": [public_filter.id],
                "passed_at": str(utcnow_naive()),
            },
            token=upload_data_token,
        )
        assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator("//*[@data-testid='savedStatusSelect']").first.click()
    page.locator("//li[@data-value='notSavedToAnyAccessible']").first.click()
    page.locator('//button[text()="Search"]').first.click()

    expect(
        page.locator('//*[contains(., "Found 1 candidates.")]').first
    ).to_be_visible()

    page.locator("//*[@data-testid='savedStatusSelect']").first.click()
    page.locator("//li[@data-value='savedToAnyAccessible']").first.click()
    page.locator('//button[text()="Search"]').first.click()

    expect(
        page.locator('//*[contains(., "Found 5 candidates.")]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_save_candidate_quick_save(
    page, group_admin_user, public_group, public_candidate
):
    page.goto(f"/become_user/{group_admin_user.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[text()="Search"]').first.click()
    expect(
        page.locator(f'//a[@data-testid="{public_candidate.id}"]').first
    ).to_be_visible()
    page.locator(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    ).first.click()
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[text()="Search"]').first.click()
    expect(
        page.locator(f'//a[@data-testid="{public_candidate.id}"]').first
    ).to_be_visible()
    expect(page.locator('//span[text()="Previously Saved"]').first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_save_candidate_select_groups(
    page, group_admin_user, public_group, public_candidate
):
    page.goto(f"/become_user/{group_admin_user.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[text()="Search"]').first.click()
    expect(
        page.locator(f'//a[@data-testid="{public_candidate.id}"]').first
    ).to_be_visible()
    page.locator(
        f'//button[@name="saveCandidateButtonDropDownArrow{public_candidate.id}"]'
    ).first.click()
    menu_option = page.locator(
        f'//*[@name="buttonMenuOption{public_candidate.id}_Select groups & save"]'
    ).first
    # the menu item only responds to a native DOM click (matches the legacy
    # execute_script click); a normal click doesn't trigger its handler.
    menu_option.evaluate("el => el.click()")
    # "Select groups & save" opens a group-select dialog directly (the split-button
    # menu stays open behind it by design -- it only closes on click-away). Wait
    # for the dialog, then save; the filtered group (public_group) is pre-checked.
    expect(
        page.locator('//*[text()="Select one or more groups:"]').first
    ).to_be_visible()
    page.locator(
        f'//button[@name="finalSaveCandidateButton{public_candidate.id}"]'
    ).first.click()
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[text()="Search"]').first.click()
    expect(page.locator('//span[text()="Previously Saved"]').first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_save_candidate_no_groups_error_message(
    page, group_admin_user, public_group, public_candidate
):
    page.goto(f"/become_user/{group_admin_user.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[text()="Search"]').first.click()
    expect(
        page.locator(f'//a[@data-testid="{public_candidate.id}"]').first
    ).to_be_visible()
    page.locator(
        f'//button[@name="saveCandidateButtonDropDownArrow{public_candidate.id}"]'
    ).first.click()
    menu_option = page.locator(
        f'//*[@name="buttonMenuOption{public_candidate.id}_Select groups & save"]'
    ).first
    # the menu item only responds to a native DOM click (matches the legacy
    # execute_script click); a normal click doesn't trigger its handler.
    menu_option.evaluate("el => el.click()")
    # "Select groups & save" opens a group-select dialog directly. Uncheck the
    # pre-selected group so none is selected, then saving must surface a
    # validation error.
    expect(
        page.locator('//*[text()="Select one or more groups:"]').first
    ).to_be_visible()
    page.locator(
        f'//*[@data-testid="saveCandGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator(
        f'//button[@name="finalSaveCandidateButton{public_candidate.id}"]'
    ).first.click()
    expect(
        page.locator('//*[contains(.,"Select at least one group")]').first
    ).to_be_visible()


def test_submit_annotations_sorting(
    page,
    view_only_user,
    public_group,
    public_candidate,
    public_candidate2,
    annotation_token,
):
    origin = str(uuid.uuid4())[:5]
    status, data = api(
        "POST",
        f"sources/{public_candidate.id}/annotations",
        data={
            "obj_id": public_candidate.id,
            "origin": origin,
            "data": {"numeric_field": 1},
        },
        token=annotation_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        f"sources/{public_candidate2.id}/annotations",
        data={
            "obj_id": public_candidate2.id,
            "origin": origin,
            "data": {"numeric_field": 2},
        },
        token=annotation_token,
    )
    assert status == 200

    # origins are cached, so wait for the cache to invalidate (5 s in test config)
    time.sleep(3)

    page.goto(f"/become_user/{view_only_user.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()

    page.locator('//input[@id="annotationSortingOriginSelect"]').first.click()
    page.locator(f'//li[text()="{origin}"]').first.click()
    page.locator('//input[@id="annotationSortingKeySelect"]').first.click()
    page.locator('//li[text()="numeric_field"]').first.click()
    page.locator('//input[@id="annotationSortingOrderSelect"]').first.click()
    page.locator('//li[text()="Ascending"]').first.click()

    page.locator('//button[text()="Search"]').first.click()
    expect(
        page.locator(f'//a[@data-testid="{public_candidate.id}"]').first
    ).to_be_visible()

    expect(
        page.locator(
            '//*[contains(@data-testid, "candidate-1")][.//*[contains(.,"1.0000")]]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            '//*[contains(@data-testid, "candidate-2")][.//*[contains(.,"2.0000")]]'
        ).first
    ).to_be_visible()

    page.locator("//button[@data-testid='sortOnAnnotationButton']").first.click()

    expect(
        page.locator(
            '//*[contains(@data-testid, "candidate-1")][.//*[contains(.,"2.0000")]]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            '//*[contains(@data-testid, "candidate-2")][.//*[contains(.,"1.0000")]]'
        ).first
    ).to_be_visible()


def test_candidate_classifications_filtering(
    page,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    taxonomy_token,
    classification_token,
):
    candidate_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": candidate_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(utcnow_naive()),
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "POST", "sources", data={"id": candidate_id}, token=upload_data_token
    )
    assert status == 200
    status, data = api(
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
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": candidate_id,
            "classification": "Algol",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator("//div[@id='classifications-select']").first.click()
    page.locator("//li[@data-value='Algol']").first.click()
    page.keyboard.press("Escape")

    page.locator('//button[text()="Search"]').first.click()
    expect(page.locator(f'//a[@data-testid="{candidate_id}"]').first).to_be_visible()

    page.locator("//div[@id='classifications-select']").first.click()
    page.locator("//li[@data-value='Algol']").first.click()
    page.locator("//li[@data-value='AGN']").first.click()
    page.keyboard.press("Escape")
    page.locator('//button[text()="Search"]').first.click()
    expect(page.locator(f'//a[@data-testid="{candidate_id}"]').first).to_be_hidden()


def test_candidate_redshift_filtering(
    page,
    user,
    public_filter,
    public_group,
    upload_data_token,
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 0,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(utcnow_naive()),
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 1,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(utcnow_naive()),
        },
        token=upload_data_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator("//input[@id='minimum-redshift']").first.fill("0")
    page.locator("//input[@id='maximum-redshift']").first.fill("0.5")
    page.locator('//button[text()="Search"]').first.click()
    expect(page.locator(f'//a[@data-testid="{obj_id1}"]').first).to_be_visible()
    expect(page.locator(f'//a[@data-testid="{obj_id2}"]').first).to_be_hidden()


def test_candidate_rejection_filtering(
    page,
    user,
    public_group,
    upload_data_token,
    public_filter,
):
    candidate_id = str(uuid.uuid4())
    status, _ = api(
        "POST",
        "candidates",
        data={
            "id": candidate_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(utcnow_naive()),
        },
        token=upload_data_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[text()="Search"]').first.click()

    page.locator(f'//*[@data-testid="rejected-visible_{candidate_id}"]').first.click()
    page.locator('//button[text()="Search"]').first.click()
    expect(
        page.locator(f'//*[@data-testid="rejected_invisible_{candidate_id}"]').first
    ).to_be_visible()

    page.locator('//*[@data-testid="rejectedStatusSelect"]').first.click()
    page.locator('//button[text()="Search"]').first.click()
    expect(
        page.locator('//*[contains(., "Found 0 candidates.")]').first
    ).to_be_visible()


def test_add_scanning_profile(
    page, user, public_group, public_source, annotation_token
):
    status, _ = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "obj_id": public_source.id,
            "origin": "kowalski",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )
    assert status == 200

    time.sleep(2)  # origins are cached; wait for invalidation

    page.goto(f"/become_user/{user.id}")
    page.goto("/candidates")
    page.locator('//button[@data-testid="manageScanningProfilesButton"]').first.click()
    page.locator('//button[@name="new_scanning_profile"]').first.click()
    time.sleep(1)  # let the form initialize / load groups

    page.locator('//div[@data-testid="profile-name"]//input').first.fill("profile1")
    page.locator('//div[@data-testid="timeRange"]//input').first.fill("48")

    page.locator('//div[@aria-labelledby="savedStatusSelectLabel"]').first.click()
    saved_status_option = "and is saved to at least one group I have access to"
    page.locator(f'//li[text()="{saved_status_option}"]').first.click()

    page.locator('//div[@data-testid="profile-minimum-redshift"]//input').first.fill(
        "0.0"
    )
    page.locator('//div[@data-testid="profile-maximum-redshift"]//input').first.fill(
        "1.0"
    )
    page.locator('//div[@data-testid="annotation-sorting-accordion"]').first.click()
    page.locator(
        '//div[@data-testid="profileAnnotationSortingOriginSelect"]'
    ).first.click()
    page.locator('//li[text()="kowalski"]').first.click()
    page.locator(
        '//div[@data-testid="profileAnnotationSortingKeySelect"]'
    ).first.click()
    page.locator('//li[text()="offset_from_host_galaxy"]').first.click()
    page.locator(
        '//div[@data-testid="profileAnnotationSortingOrderSelect"]'
    ).first.click()
    page.locator('//li[text()="Descending"]').first.click()

    page.locator(
        f'//span[@data-testid="profileFilteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()

    page.locator('//button[@data-testid="saveScanningProfileButton"]').first.click()
    expect(page.locator(f'//div[text()="{saved_status_option}"]').first).to_be_visible()

    page.locator('//button[@data-testid="closeScanningProfilesButton"]').first.click()
    expect(
        page.locator('//input[@id="minimum-redshift"][@value="0.0"]').first
    ).to_be_visible()
    expect(
        page.locator('//input[@id="maximum-redshift"][@value="1.0"]').first
    ).to_be_visible()
    expect(
        page.locator(
            f'//span[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
        ).first
    ).to_be_visible()
    expect(
        page.locator('//input[@value="offset_from_host_galaxy"]').first
    ).to_be_visible()
    expect(page.locator('//input[@value="Descending"]').first).to_be_visible()


def test_delete_scanning_profile(page, user, public_group):
    page.goto(f"/become_user/{user.id}")
    page.goto("/candidates")
    page.locator('//button[@data-testid="manageScanningProfilesButton"]').first.click()
    page.locator('//button[@name="new_scanning_profile"]').first.click()
    time.sleep(1)

    page.locator('//div[@data-testid="profile-name"]//input').first.fill("profile1")
    page.locator('//div[@data-testid="timeRange"]//input').first.fill("123")

    page.locator(
        f'//span[@data-testid="profileFilteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()

    page.locator('//button[@data-testid="saveScanningProfileButton"]').first.click()
    expect(page.locator('//div[text()="123hrs"]').first).to_be_visible()

    page.locator('//button[@id="delete_button_0"]').first.click()
    expect(page.locator('//div[text()="123hrs"]').first).to_be_hidden()


@pytest.mark.flaky(reruns=2)
def test_load_scanning_profile(
    page, user, public_group, public_source, annotation_token
):
    page.goto(f"/become_user/{user.id}")
    page.goto("/candidates")

    page.locator('//button[@data-testid="manageScanningProfilesButton"]').first.click()
    page.locator('//button[@name="new_scanning_profile"]').first.click()
    time.sleep(1)

    page.locator('//div[@data-testid="profile-maximum-redshift"]//input').first.fill(
        "0.5"
    )
    page.locator('//div[@data-testid="profile-name"]//input').first.fill("profile1")
    page.locator(
        f'//span[@data-testid="profileFilteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[@data-testid="saveScanningProfileButton"]').first.click()
    expect(page.locator('//div[contains(text(), "0.5")]').first).to_be_visible()

    page.locator('//button[@name="new_scanning_profile"]').first.click()

    page.locator('//div[@data-testid="profile-maximum-redshift"]//input').first.fill(
        "1.0"
    )
    page.locator('//div[@data-testid="profile-name"]//input').first.fill("profile2")
    page.locator(
        f'//span[@data-testid="profileFilteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[@data-testid="saveScanningProfileButton"]').first.click()
    expect(page.locator('//div[contains(text(), "1.0")]').first).to_be_visible()

    page.locator('//span[@data-testid="loaded_0"]').first.click()

    page.locator('//button[@data-testid="closeScanningProfilesButton"]').first.click()
    expect(
        page.locator('//input[@id="maximum-redshift"][@value="0.5"]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=3)
def test_user_without_save_access_cannot_save(
    page, super_admin_token, public_group, public_candidate, user_group2
):
    status, data = api(
        "POST",
        f"groups/{public_group.id}/users",
        data={"userID": user_group2.id, "admin": False, "canSave": False},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"groups/{public_group.id}?includeGroupUsers=true",
        token=super_admin_token,
    )
    group_user = None
    for gu in data["data"]["users"]:
        if gu["id"] == user_group2.id:
            group_user = gu
    assert group_user is not None
    assert not group_user["can_save"]
    assert not group_user["admin"]

    page.goto(f"/become_user/{user_group2.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[text()="Search"]').first.click()
    expect(
        page.locator(f'//a[@data-testid="{public_candidate.id}"]').first
    ).to_be_visible()
    page.locator(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    ).first.click()


@pytest.mark.flaky(reruns=2)
def test_add_classification_on_scanning_page(
    page, user, public_group, taxonomy_token, public_filter, upload_data_token
):
    from ..users_groups_and_content.test_profile import add_classification_shortcut

    shortcut_name = add_classification_shortcut(
        page, user, public_group, taxonomy_token
    )
    page.goto(f"/become_user/{user.id}")
    candidate_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": f"{candidate_id}",
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "passed_at": str(utcnow_naive()),
            "filter_ids": [public_filter.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[text()="Search"]').first.click()
    page.locator(
        f'//button[@data-testid="saveCandidateButton_{candidate_id}"]'
    ).first.click()

    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()
    page.locator('//button[text()="Search"]').first.click()

    page.locator(
        f'//button[@data-testid="addClassificationsButton_{candidate_id}"]'
    ).first.click()
    page.locator(f'//button[@data-testid="{shortcut_name}_inDialog"]').first.click()
    page.locator(
        '//button[@data-testid="addClassificationsButtonInDialog"]'
    ).first.click()

    page.goto(f"/source/{candidate_id}")
    expect(page.locator('//span[contains(text(), "AGN")]').first).to_be_visible()
    expect(page.locator('//span[contains(text(), "AM CVn")]').first).to_be_visible()
