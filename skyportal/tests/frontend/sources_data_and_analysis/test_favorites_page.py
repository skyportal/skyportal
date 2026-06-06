import uuid

import pytest
from playwright.sync_api import expect

from skyportal.model_util import create_token
from skyportal.tests import api


@pytest.mark.flaky(reruns=3)
def test_add_remove_favorites(page, user, public_source):
    page.goto(f"/become_user/{user.id}")

    # go to source page, wait until it finishes loading
    page.goto(f"/source/{public_source.id}")

    # click the empty favorites button
    page.locator(
        f'//*[@data-testid="favorites-exclude_{public_source.id}"]'
    ).first.click()

    # a filled favorites button means it was added successfully
    expect(
        page.locator(f'//*[@data-testid="favorites-include_{public_source.id}"]').first
    ).to_be_visible()

    # go to the favorite page
    page.goto("/favorites")

    expect(
        page.locator(f"//a[contains(@href, '/source/{public_source.id}')]").first
    ).to_be_visible()
    expect(
        page.locator(
            f"//*[contains(@data-testid, 'favorites-include_{public_source.id}')]"
        ).first
    ).to_be_visible()

    # click to un-save the source as favorite
    page.locator(
        f'//*[@data-testid="favorites-include_{public_source.id}"]'
    ).first.click()

    expect(
        page.locator(
            '//*[contains(text(), "No sources have been saved as favorites.")]'
        ).first
    ).to_be_visible()


def test_add_favorites_from_api(page, super_admin_user, public_group):
    token_id = create_token(
        ACLs=["Upload data"], user_id=super_admin_user.id, name=str(uuid.uuid4())
    )
    obj_id = str(uuid.uuid4())

    status, data = api(
        "POST",
        "sources",
        data={
            "id": f"{obj_id}",
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 0.153,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=token_id,
    )
    assert status == 200
    assert data["data"]["id"] == f"{obj_id}"

    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": super_admin_user.id,
            "obj_id": obj_id,
            "list_name": "favorites",
        },
        token=token_id,
    )
    assert status == 200

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/group_sources/{public_group.id}")

    page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()
    page.locator("//input[@name='sourceID']").first.fill(obj_id)
    page.locator("//button[text()='Submit']").first.click()

    expect(
        page.locator(f"//a[contains(@href, '/source/{obj_id}')]").first
    ).to_be_visible()

    # click the filled star to un-save this source
    page.locator(f'//*[@data-testid="favorites-include_{obj_id}"]').first.click()

    page.goto("/favorites")
    expect(
        page.locator(
            '//*[contains(text(), "No sources have been saved as favorites.")]'
        ).first
    ).to_be_visible()


def test_remove_favorites_from_api(page, super_admin_user, public_group):
    token_id = create_token(
        ACLs=["Upload data"], user_id=super_admin_user.id, name=str(uuid.uuid4())
    )
    obj_id = str(uuid.uuid4())

    status, data = api(
        "POST",
        "sources",
        data={
            "id": f"{obj_id}",
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 0.153,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=token_id,
    )
    assert status == 200
    assert data["data"]["id"] == f"{obj_id}"

    status, data = api(
        "POST",
        "listing",
        data={
            "user_id": super_admin_user.id,
            "obj_id": obj_id,
            "list_name": "favorites",
        },
        token=token_id,
    )
    assert status == 200
    listing_id = data["data"]["id"]

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/favorites")

    expect(
        page.locator(f"//a[contains(@href, '/source/{obj_id}')]").first
    ).to_be_visible()

    status, data = api("DELETE", f"listing/{listing_id}", token=token_id)
    assert status == 200

    page.goto("/favorites")
    expect(
        page.locator(
            '//*[contains(text(), "No sources have been saved as favorites.")]'
        ).first
    ).to_be_visible()
