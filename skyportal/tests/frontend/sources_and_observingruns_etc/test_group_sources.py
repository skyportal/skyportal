import uuid
from datetime import UTC, datetime, timezone

import pytest
from playwright.sync_api import expect
from tdtax import __version__, taxonomy

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_add_new_source_renders_on_group_sources_page(
    page,
    super_admin_user_two_groups,
    public_group,
    public_group2,
    upload_data_token_two_groups,
    taxonomy_token_two_groups,
    classification_token_two_groups,
):
    page.goto(f"/become_user/{super_admin_user_two_groups.id}")
    page.goto(f"/group_sources/{public_group.id}")
    expect(
        page.locator(f"//*[text()[contains(., '{public_group.name}')]]").first
    ).to_be_visible()

    obj_id = str(uuid.uuid4())
    t0 = datetime.now(UTC)

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
            "group_ids": [public_group.id, public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == f"{obj_id}"

    page.goto(f"/group_sources/{public_group.id}")
    expect(
        page.locator(f"//a[contains(@href, '/source/{obj_id}')]").first
    ).to_be_visible()
    expect(
        page.locator(
            f"//*[text()[contains(., '{t0.strftime('%Y-%m-%dT%H:%M')}')]]"
        ).first
    ).to_be_visible()
    expect(page.locator("//*[text()[contains(., '0.153')]]").first).to_be_visible()

    page.locator("//*[@id='expandable-button']").first.click()
    expect(
        page.locator(f'//*[@data-testid="groupSourceExpand_{obj_id}"]').first
    ).to_be_visible()

    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id, public_group2.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token_two_groups,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": obj_id,
            "classification": "Algol",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group.id],
        },
        token=classification_token_two_groups,
    )
    assert status == 200
    expect(page.locator("//*[text()[contains(., 'Algol')]]").first).to_be_visible()

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": obj_id,
            "classification": "RS CVn",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group2.id],
        },
        token=classification_token_two_groups,
    )
    assert status == 200
    expect(page.locator("//*[text()[contains(., 'RS CVn')]]").first).to_be_visible()
    expect(page.locator("//*[text()[contains(., 'Algol')]]").first).to_be_visible()


def test_request_source(
    page,
    super_admin_user_two_groups,
    public_group,
    public_group2,
    upload_data_token,
    upload_data_token_two_groups,
):
    page.goto(f"/become_user/{super_admin_user_two_groups.id}")
    page.goto(f"/group_sources/{public_group.id}")
    expect(
        page.locator(f"//*[text()[contains(., '{public_group.name}')]]").first
    ).to_be_visible()

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
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["data"]["id"] == f"{obj_id}"

    page.goto(f"/group_sources/{public_group2.id}")
    # The source is in group1 only, so it must not appear on group2's page yet.
    expect(
        page.locator(f"//*[text()[contains(., '{public_group2.name}')]]").first
    ).to_be_visible()
    page.wait_for_timeout(2000)
    expect(page.locator(f"//a[contains(@href, '/source/{obj_id}')]")).to_have_count(0)

    status, data = api(
        "POST",
        "source_groups",
        data={"objId": f"{obj_id}", "inviteGroupIds": [public_group2.id]},
        token=upload_data_token,
    )
    assert status == 200

    page.goto(f"/group_sources/{public_group2.id}")
    expect(
        page.locator("//*[text()[contains(., 'Requested to save')]]").first
    ).to_be_visible()
    expect(
        page.locator(f"//a[contains(@href, '/source/{obj_id}')]").first
    ).to_be_visible()
    expect(page.locator("//*[text()[contains(., 'Save')]]").first).to_be_visible()
    expect(page.locator("//*[text()[contains(., 'Ignore')]]").first).to_be_visible()


def test_sources_sorting(page, super_admin_user, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    status, data = api(
        "POST",
        "sources",
        data={
            "id": f"{obj_id}",
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 0.0,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == f"{obj_id}"
    status, data = api(
        "POST",
        "sources",
        data={
            "id": f"{obj_id2}",
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 0.153,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == f"{obj_id2}"

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/group_sources/{public_group.id}")
    expect(
        page.locator(f"//*[text()[contains(., '{public_group.name}')]]").first
    ).to_be_visible()

    # Sort by date saved desc by clicking the header twice
    page.locator("//*[text()='Saved at']").first.click()
    page.locator("//*[text()='Saved at']").first.click()

    expect(
        page.locator(f'//div[@data-rowindex="0"]//span[text()="{obj_id2}"]').first
    ).to_be_visible()
    expect(
        page.locator(f'//div[@data-rowindex="1"]//span[text()="{obj_id}"]').first
    ).to_be_visible()

    # Sort by redshift ascending, which puts obj_id first
    page.locator("//*[text()='Redshift']").first.click()

    expect(
        page.locator(f'//div[@data-rowindex="0"]//span[text()="{obj_id}"]').first
    ).to_be_visible()
    expect(
        page.locator(f'//div[@data-rowindex="1"]//span[text()="{obj_id2}"]').first
    ).to_be_visible()
