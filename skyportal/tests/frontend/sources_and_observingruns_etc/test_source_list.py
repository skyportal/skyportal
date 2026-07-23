import uuid
from datetime import timedelta

import pytest
from dateutil import parser
from playwright.sync_api import expect
from tdtax import __version__, taxonomy

from baselayer.app.config import load_config
from skyportal.tests import api

from ....utils.naive_datetime import utcnow_naive

cfg = load_config()


def _filter_by_source_id(page, source_id):
    page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()
    page.locator("//input[@name='sourceID']").first.fill(source_id)
    page.locator("//button[text()='Submit']").first.click()


@pytest.mark.flaky(reruns=3)
def test_add_sources_two_groups(
    page,
    super_admin_user_two_groups,
    public_group,
    public_group2,
    upload_data_token_two_groups,
    taxonomy_token_two_groups,
    classification_token_two_groups,
):
    obj_id = str(uuid.uuid4())
    t1 = utcnow_naive()

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

    page.goto(f"/become_user/{super_admin_user_two_groups.id}")
    assert "localhost" in page.url
    page.goto("/sources")

    _filter_by_source_id(page, obj_id)

    expect(
        page.locator(f"//a[contains(@href, '/source/{obj_id}')]").first
    ).to_be_visible()

    saved_at_element = page.locator(
        f"//*[text()[contains(., '{t1.strftime('%Y-%m-%dT%H:%M')}')]]"
    ).first
    expect(saved_at_element).to_be_visible()
    saved_group1 = parser.parse(saved_at_element.inner_text())
    assert abs(saved_group1 - t1) < timedelta(seconds=30)

    expect(page.locator("//*[text()[contains(., '0.153')]]").first).to_be_visible()

    page.locator("//div[@data-rowindex='0']//*[@id='expandable-button']").first.click()
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

    # classification should not show up without a page refresh
    expect(page.locator("//*[text()[contains(., 'Algol')]]").first).to_be_hidden()

    _filter_by_source_id(page, obj_id)
    expect(page.locator("//*[text()[contains(., 'Algol')]]").first).to_be_visible()

    t2 = utcnow_naive()
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
            "group_ids": [public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["status"] == "success"

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

    _filter_by_source_id(page, obj_id)

    expect(page.locator("//*[text()[contains(., 'RS CVn')]]").first).to_be_visible()

    saved_at_element = page.locator(
        f"//*[text()[contains(., '{t2.strftime('%Y-%m-%dT%H:%M')}')]]"
    ).first
    expect(saved_at_element).to_be_visible()
    saved_group2 = parser.parse(saved_at_element.inner_text())
    assert abs(saved_group2 - t2) < timedelta(seconds=2)

    assert saved_group2 > saved_group1


@pytest.mark.flaky(reruns=2)
def test_filter_by_classification(
    page, user, public_group, upload_data_token, taxonomy_token, classification_token
):
    source_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": source_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    taxonomy_name = "test taxonomy" + str(uuid.uuid4())
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": taxonomy_name,
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
            "obj_id": source_id,
            "classification": "Algol",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/sources")

    page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()
    page.locator("//div[@data-testid='classifications-select']").first.click()
    page.locator(f"//li[@data-value='{taxonomy_name}: Algol']").first.click()
    page.keyboard.press("Escape")
    page.locator("//button[text()='Submit']").first.click()

    expect(page.locator(f'//a[@data-testid="{source_id}"]').first).to_be_visible()

    page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()
    page.locator("//div[@data-testid='classifications-select']").first.click()
    page.locator(f"//li[@data-value='{taxonomy_name}: AGN']").first.click()
    page.keyboard.press("Escape")
    page.locator("//button[text()='Submit']").first.click()
    expect(page.locator(f'//a[@data-testid="{source_id}"]').first).to_be_hidden()


def test_filter_by_spectrum_time(page, user, public_group, upload_data_token, lris):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id1
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id2

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": obj_id1,
            "observed_at": str(utcnow_naive().strftime("%Y-%m-%dT%H:%M:%S")),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": obj_id2,
            "observed_at": str(
                (utcnow_naive() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
            ),
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{user.id}")
    page.goto("/sources")

    test_time = utcnow_naive().strftime("%Y-%m-%dT%H:%M:%S")

    page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()
    page.locator("//div[@data-testid='hasSpectrumBeforeTest']").first.click()
    page.locator("//div[@data-testid='hasSpectrumBeforeTest']//input").first.fill(
        test_time
    )
    page.locator("//button[text()='Submit']").first.click()

    expect(page.locator(f'//a[@data-testid="{obj_id1}"]').first).to_be_visible()

    page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()
    page.locator("//div[@data-testid='hasSpectrumAfterTest']").first.click()
    page.locator("//div[@data-testid='hasSpectrumAfterTest']//input").first.fill(
        test_time
    )
    page.locator("//button[text()='Submit']").first.click()

    expect(page.locator(f'//a[@data-testid="{obj_id2}"]').first).to_be_visible()


def test_hr_diagram(page, user, public_group, upload_data_token, annotation_token):
    source_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": source_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")

    status, data = api(
        "POST",
        f"sources/{source_id}/annotations",
        data={
            "origin": "gaiadr3.gaia_source",
            "data": {"Mag_G": 11.3, "Mag_Bp": 11.8, "Mag_Rp": 11.0, "Plx": 20},
        },
        token=annotation_token,
    )
    assert status == 200

    page.goto("/sources")

    _filter_by_source_id(page, source_id)

    expect(
        page.locator(f"//a[contains(@href, '/source/{source_id}')]").first
    ).to_be_visible()

    page.locator("//*[@id='expandable-button']").first.click()
    expect(
        page.locator(f'//*[@data-testid="groupSourceExpand_{source_id}"]').first
    ).to_be_visible()
    expect(
        page.locator(f'//div[@data-testid="hr_diagram_{source_id}"]').first
    ).to_be_visible()
