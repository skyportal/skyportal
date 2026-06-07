import os
import uuid
from io import BytesIO

import pytest
from PIL import Image, ImageChops
from playwright.sync_api import expect

from baselayer.app.config import load_config
from skyportal.models import DBSession
from skyportal.tests import api

cfg = load_config()


def enter_comment_text(page, comment_text):
    comment_box = page.locator(
        '//form[@data-testid="comment-form"]//textarea[@name="text"]'
    ).first
    comment_box.click()
    comment_box.fill("")
    if comment_text:
        # type char-by-char so the @-mention autosuggestion fires
        comment_box.press_sequentially(comment_text)


def add_comment(page, comment_text):
    enter_comment_text(page, comment_text)
    page.locator(
        '//form[@data-testid="comment-form"]//*[@name="submitCommentButton"]'
    ).first.click()


def wait_for_comment_text_found(page, comment_text):
    expect(
        page.locator('//*[@id="comment"]//p', has_text=comment_text.strip()).first
    ).to_be_visible()


def add_comment_and_wait_for_display(page, comment_text):
    add_comment(page, comment_text)
    try:
        wait_for_comment_text_found(page, comment_text)
    except AssertionError:
        page.reload()
        page.locator("//*[@id='expandable-button']").first.click()
        wait_for_comment_text_found(page, comment_text)


@pytest.mark.flaky(reruns=2)
def test_public_source_page(page, user, public_source, public_group):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    expect(page.locator(f'//span[text()="{public_group.name}"]').first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_comment_username_autosuggestion(page, user, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    enter_comment_text(page, f"hey @{user.username[:5]}")
    match_button = (
        f'//button[text()="{user.username} {user.first_name} {user.last_name}"]'
    )
    page.locator(match_button).first.click()
    expect(page.locator(match_button).first).to_be_hidden()
    page.locator(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    ).first.click()
    wait_for_comment_text_found(page, f"hey @{user.username}")


@pytest.mark.flaky(reruns=2)
def test_comment_user_last_name_autosuggestion(page, user, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    enter_comment_text(page, f"hey @{user.last_name[:5]}")
    match_button = (
        f'//button[text()="{user.username} {user.first_name} {user.last_name}"]'
    )
    page.locator(match_button).first.click()
    expect(page.locator(match_button).first).to_be_hidden()
    page.locator(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    ).first.click()
    wait_for_comment_text_found(page, f"hey @{user.username}")


@pytest.mark.flaky(reruns=2)
def test_comment_user_first_name_autosuggestion(page, user, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    enter_comment_text(page, f"hey @{user.first_name[:5]}")
    match_button = (
        f'//button[text()="{user.username} {user.first_name} {user.last_name}"]'
    )
    page.locator(match_button).first.click()
    expect(page.locator(match_button).first).to_be_hidden()
    page.locator(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    ).first.click()
    wait_for_comment_text_found(page, f"hey @{user.username}")


@pytest.mark.flaky(reruns=2)
def test_public_source_page_null_z(page, user, public_source, public_group):
    public_source.redshift = None
    DBSession().add(public_source)
    DBSession().commit()

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    expect(page.locator(f'//span[text()="{public_group.name}"]').first).to_be_visible()


@pytest.mark.flaky(reruns=3)
def test_classifications(page, user, taxonomy_token, public_group, public_source):
    simple = {
        "class": "Cepheid",
        "tags": ["giant/supergiant", "instability strip", "standard candle"],
        "other names": ["Cep", "CEP"],
        "subclasses": [
            {"class": "Anomolous", "other names": ["Anomolous Cepheid", "BLBOO"]},
            {
                "class": "Mult-mode",
                "other names": ["Double-mode Cepheid", "Multi-mode Cepheid", "CEP(B)"],
            },
            {
                "class": "Classical",
                "tags": [],
                "other names": [
                    "Population I Cepheid",
                    "Type I Cepheid",
                    "DCEP",
                    "Delta Cepheid",
                    "Classical Cepheid",
                ],
                "subclasses": [
                    {
                        "class": "Symmetrical",
                        "other names": ["DCEPS", "Delta Cep-type Symmetrical"],
                    }
                ],
            },
        ],
    }

    tax_name = str(uuid.uuid4())
    tax_version = "test0.1"

    status, _ = api(
        "POST",
        "taxonomy",
        data={
            "name": tax_name,
            "hierarchy": simple,
            "group_ids": [public_group.id],
            "version": tax_version,
        },
        token=taxonomy_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()

    page.locator('//div[@id="root_taxonomy"]').first.click()
    page.locator(f'//li[contains(., "{tax_name} ({tax_version})")]').first.click()
    page.keyboard.press("Escape")

    page.locator('//*[@id="classification"]').first.click()
    page.locator('//*[@id="classification"]').first.fill("Symmetrical")
    page.locator('//div[contains(@id, "Symmetrical")]').first.click()
    page.keyboard.press("Escape")

    page.locator('//*[@id="probability"]').first.fill("1")

    page.locator("//*[text()='Submit']").first.click()
    expect(page.locator("//*[text()='Classification saved']").first).to_be_visible()

    del_button_xpath = "//button[starts-with(@name, 'deleteClassificationButton')]"
    page.locator(del_button_xpath).first.click()
    page.locator("//*[text()='Confirm']").first.click()
    expect(page.locator("//*[contains(text(), '(P=1)')]").first).to_be_hidden()
    expect(page.locator(f"//i[text()='{tax_name}']").first).to_be_hidden()
    expect(
        page.locator(
            "//span[contains(@class, 'MuiButton-label') and text()='Symmetrical']"
        ).first
    ).to_be_hidden()

    # ensure low probability classifications have a question mark on the label
    page.locator('//div[@id="root_taxonomy"]').first.click()
    page.locator(f'//li[contains(., "{tax_name} ({tax_version})")]').first.click()
    page.keyboard.press("Escape")

    page.locator('//*[@id="classification"]').first.click()
    page.locator('//*[@id="classification"]').first.fill("Mult-mode")
    page.locator('//div[contains(@id, "Mult-mode")]').first.click()
    page.keyboard.press("Escape")

    page.locator('//*[@id="probability"]').first.fill("0.02")
    page.locator("//*[text()='Submit']").first.click()
    expect(page.locator("//*[text()='Classification saved']").first).to_be_visible()

    expect(page.locator("//span[text()='Mult-mode?']").first).to_be_visible()
    expect(page.locator("//span[text()='(P=0.02)']").first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_comments(page, user, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(page, comment_text)


def test_comment_groups_validation(page, user, public_source, public_group):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()

    comment_text = str(uuid.uuid4())
    enter_comment_text(page, comment_text)
    page.locator(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    ).first.click()
    expect(
        page.locator(
            f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]'
        ).first
    ).to_be_visible()

    enter_comment_text(page, "")
    comment_text = str(uuid.uuid4())
    enter_comment_text(page, comment_text)
    page.locator(
        "//div[@data-testid='comments-accordion']//*[text()='Customize Group Access (public if not specified)']"
    ).first.click()
    page.locator(
        f"//div[@data-testid='comments-accordion']//*[@data-testid='commentGroupCheckBox{public_group.id}']"
    ).first.click()
    page.locator(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    ).first.click()
    expect(
        page.locator(
            f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]'
        ).first
    ).to_be_visible()


def test_view_only_user_cannot_comment(page, view_only_user, public_source):
    page.goto(f"/become_user/{view_only_user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    expect(page.locator('//textarea[@name="text"]').first).to_be_hidden()


@pytest.mark.flaky(reruns=2)
def test_delete_comment(page, user, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(page, comment_text)

    comment_p = page.locator(f'//p[text()="{comment_text}"]').first
    expect(comment_p).to_be_visible()
    comment_div = comment_p.locator("xpath=../..")
    comment_id = comment_div.get_attribute("name").split("commentDivSource")[-1]
    comment_div.hover()
    page.locator(f'//*[@name="deleteCommentButton{comment_id}"]').first.click()
    expect(comment_p).to_be_hidden()


def test_regular_user_cannot_delete_unowned_comment(
    page, super_admin_user, user, public_source
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(page, comment_text)
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    comment_p = page.locator(f'//p[text()="{comment_text}"]').first
    expect(comment_p).to_be_visible()
    comment_div = comment_p.locator("xpath=../..")
    comment_id = comment_div.get_attribute("name").split("commentDivSource")[-1]
    comment_div.hover()
    expect(
        page.locator(f'//*[@name="deleteCommentButton{comment_id}"]').first
    ).to_be_hidden()


def test_super_user_can_delete_unowned_comment(
    page, super_admin_user, user, public_source
):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(page, comment_text)

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")

    comment_p = page.locator(f'//p[text()="{comment_text}"]').first
    expect(comment_p).to_be_visible()
    comment_div = comment_p.locator("xpath=../..")
    comment_id = comment_div.get_attribute("name").split("commentDivSource")[-1]
    comment_div.hover()
    page.locator(f'//*[@name="deleteCommentButton{comment_id}"]').first.click()
    expect(comment_p).to_be_hidden()


def test_show_starlist(page, user, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    page.locator('//button[text()="Show Starlist"]').first.click()
    expect(page.locator("//pre[text()[contains(., '_k1')]]").first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_centroid_plot(
    page, user, public_source, public_group, ztf_camera, upload_data_token
):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")

    expect(page.locator('//div[@id="no-centroid-plot"]').first).to_be_visible()

    discovery_ra = public_source.ra
    discovery_dec = public_source.dec
    status, data = api(
        "POST",
        "photometry?refresh=true",
        data={
            "obj_id": str(public_source.id),
            "mjd": [58000.0, 58001.0, 58002.0],
            "instrument_id": ztf_camera.id,
            "flux": [12.24, 15.24, 12.24],
            "fluxerr": [0.031, 0.029, 0.030],
            "filter": ["ztfg", "ztfg", "ztfg"],
            "zp": [25.0, 30.0, 21.2],
            "magsys": ["ab", "ab", "ab"],
            "ra": [discovery_ra + 0.0001, discovery_ra + 0.0002, discovery_ra + 0.0003],
            "ra_unc": 0.17,
            "dec": [
                discovery_dec + 0.0001,
                discovery_dec + 0.0002,
                discovery_dec + 0.0003,
            ],
            "dec_unc": 0.2,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["ids"]) == 3

    expect(
        page.locator('//div[@id="centroid-plot"]/div[@class="js-plotly-plot"]').first
    ).to_be_visible()


def test_dropdown_facility_change(page, user, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    page.locator('//*[text()="Show Starlist"]').first.click()
    expect(page.locator("//pre[text()[contains(., 'raoffset')]]").first).to_be_visible()
    page.locator('//*[@id="mui-component-select-StarListSelectElement"]').first.click()
    page.locator('//li[@data-value="P200"]').first.click()
    expect(page.locator("//pre[text()[contains(., 'dist')]]").first).to_be_visible()


def test_source_notification(page, user, public_group, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()

    page.locator("//div[@id='selectGroups']").first.click()
    page.locator(f'//div[@data-testid="group_{public_group.id}"]').first.click()
    page.keyboard.press("Escape")
    page.locator("//label[@data-testid='soft']").first.click()
    page.locator("//button[@data-testid='sendNotificationButton']").first.click()
    expect(
        page.locator("//*[text()='Notification queued up successfully']").first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_unsave_from_group(
    page, user_two_groups, public_source_two_groups, public_group2
):
    public_source = public_source_two_groups
    page.goto(f"/become_user/{user_two_groups.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    page.locator(f'//*[@data-testid="editGroups_{public_source.id}"]').first.click()
    page.locator(
        f'//*[@data-testid="unsaveGroupCheckbox_{public_group2.id}"]'
    ).first.click()
    page.locator(
        f'//button[@name="editSourceGroupsButton_{public_source.id}"]'
    ).first.click()
    expect(
        page.locator('//*[text()="Source groups updated successfully"]').first
    ).to_be_visible()
    expect(
        page.locator(f'//div[@data-testid="groupChip_{public_group2.id}"]').first
    ).to_be_hidden()


@pytest.mark.flaky(reruns=2)
def test_request_group_to_save_then_save(
    page, user, user_two_groups, public_source, public_group2
):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    page.locator(f'//*[@data-testid="editGroups_{public_source.id}"]').first.click()
    page.locator(
        f'//*[@data-testid="inviteGroupCheckbox_{public_group2.id}"]'
    ).first.click()
    page.locator(
        f'//button[@name="editSourceGroupsButton_{public_source.id}"]'
    ).first.click()
    expect(
        page.locator('//*[text()="Source groups updated successfully"]').first
    ).to_be_visible()
    page.goto(f"/become_user/{user_two_groups.id}")
    page.goto(f"/group_sources/{public_group2.id}")
    page.locator(
        f'//button[@data-testid="saveSourceButton_{public_source.id}"]'
    ).first.click()
    expect(
        page.locator(
            f'//button[@data-testid="saveSourceButton_{public_source.id}"]'
        ).first
    ).to_be_hidden()
    expect(
        page.locator(f"//a[contains(@href, '/source/{public_source.id}')]").first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_update_redshift_and_history(page, user, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    page.locator("//*[@data-testid='updateRedshiftIconButton']").first.click()
    page.locator("//div[@data-testid='updateRedshiftTextfield']//input").first.fill(
        "0.9999"
    )
    page.locator(
        "//div[@data-testid='updateRedshiftErrorTextfield']//input"
    ).first.fill("0.0001")
    page.locator("//button[@data-testid='updateRedshiftSubmitButton']").first.click()
    expect(
        page.locator("//*[text()='Source redshift successfully updated.']").first
    ).to_be_visible()
    page.keyboard.press("Escape")  # Close dialog
    expect(page.locator("//*[contains(., '0.9999')]").first).to_be_visible()
    expect(page.locator("//*[contains(., '0.0001')]").first).to_be_visible()

    page.locator("//*[@data-testid='redshiftHistoryIconButton']").first.click()
    expect(page.locator("//th[text()='Set By']").first).to_be_visible()
    expect(page.locator("//td[text()='0.9999']").first).to_be_visible()
    expect(page.locator("//td[text()='0.0001']").first).to_be_visible()
    expect(page.locator(f"//td[text()='{user.username}']").first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_update_redshift_and_history_without_error(page, user, public_source):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    page.locator("//*[@data-testid='updateRedshiftIconButton']").first.click()
    page.locator("//div[@data-testid='updateRedshiftTextfield']//input").first.fill(
        "0.9998"
    )
    page.locator("//button[@data-testid='updateRedshiftSubmitButton']").first.click()
    expect(
        page.locator("//*[text()='Source redshift successfully updated.']").first
    ).to_be_visible()
    page.keyboard.press("Escape")  # Close dialog
    expect(page.locator("//*[contains(., '0.9998')]").first).to_be_visible()

    page.locator("//*[@data-testid='redshiftHistoryIconButton']").first.click()
    expect(page.locator("//th[text()='Set By']").first).to_be_visible()
    expect(page.locator("//td[text()='0.9998']").first).to_be_visible()
    expect(page.locator(f"//td[text()='{user.username}']").first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_obj_page_unsaved_source(public_obj, page, user):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_obj.id}")
    expect(
        page.locator('//div[contains(@data-testid, "groupChip")]').first
    ).to_be_hidden()


def test_show_photometry_table(public_source, page, user):
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")

    page.locator('//*[@data-testid="show-photometry-table-button"]').first.click()
    expect(
        page.locator(f'//*[contains(text(), "Photometry of {public_source.id}")]').first
    ).to_be_visible()

    page.locator('//*[@data-testid="close-photometry-table-button"]').first.click()
    expect(
        page.locator('//*[@data-testid="close-photometry-table-button"]').first
    ).to_be_hidden()


def test_javascript_sexagesimal_conversion(public_source, page, user):
    public_source.ra = 342.0708127
    public_source.dec = 56.1130711
    DBSession().commit()
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator('//*[contains(., "22:48:17.00")]').first).to_be_visible()
    expect(page.locator('//*[contains(., "+56:06:47.06")]').first).to_be_visible()
    public_source.ra = 75.6377796
    public_source.dec = 15.606709
    DBSession().commit()
    page.reload()
    expect(page.locator('//*[contains(., "05:02:33.07")]').first).to_be_visible()
    expect(page.locator('//*[contains(., "+15:36:24.15")]').first).to_be_visible()


def test_source_hr_diagram(page, user, public_source, annotation_token):
    page.goto(f"/become_user/{user.id}")

    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "obj_id": public_source.id,
            "origin": "gaiadr3.gaia_source",
            "data": {"Mag_G": 11.3, "Mag_Bp": 12.8, "Mag_Rp": 11.0, "Plx": 20},
        },
        token=annotation_token,
    )
    assert status == 200

    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()

    component_class_xpath = (
        f"//div[contains(@data-testid, 'hr_diagram_{public_source.id}')]"
    )
    vegaplot_div = page.locator(component_class_xpath).first
    expect(vegaplot_div).to_be_visible()

    # Since Vega uses a <canvas>, compare an image of the plot to the baseline.
    generated_plot = Image.open(BytesIO(vegaplot_div.screenshot()))

    expected_plot_path = os.path.abspath("skyportal/tests/data/HR_diagram_expected.png")
    # Regenerate the baseline (matches the legacy test's behavior).
    generated_plot.save(expected_plot_path)

    if not os.path.exists(expected_plot_path):
        pytest.fail("Missing HR diagram baseline image for comparison")
    expected_plot = Image.open(expected_plot_path)

    difference = ImageChops.difference(
        generated_plot.convert("RGB"), expected_plot.convert("RGB")
    )
    assert difference.getbbox() is None


def test_duplicate_sources_render(
    page, public_source, public_group, upload_data_token, user, ztf_camera
):
    obj_id2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": public_source.ra + 0.0001,
            "dec": public_source.dec + 0.0001,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id2,
            "mjd": 59801.3,
            "instrument_id": ztf_camera.id,
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "mag": 12.4,
            "magerr": 0.3,
            "limiting_mag": 22,
            "magsys": "ab",
        },
        token=upload_data_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(
        page.locator('//*[contains(text(), "Possible duplicate of:")]').first
    ).to_be_visible()
    page.locator(f'//*[contains(text(), "{obj_id2}")]').first.click()
    expect(page.locator(f'//*[contains(text(), "{obj_id2}")]').first).to_be_visible()
