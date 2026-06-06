import pytest
from playwright.sync_api import expect

CSV = (
    "mjd,flux,fluxerr,zp,magsys,filter\n58001,55,1,25,ab,sdssg\n58002,53,1,25,ab,sdssg"
)


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_csv(
    page, sedm, super_admin_user, public_source, super_admin_token, public_group
):
    inst_id = sedm.id
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/upload_photometry/{public_source.id}")
    page.locator('//textarea[@name="csvData"]').first.fill(CSV)

    # instrument select
    page.locator('//*[@aria-labelledby="instrumentSelectLabel"]').first.click()
    page.locator(f'//li[@data-value="{inst_id}"]').first.click()
    page.keyboard.press("Escape")

    # group select
    page.locator('//div[@id="selectGroups"]').first.click()
    page.locator(f'//li[@data-value="{public_group.id}"]').first.click()
    page.keyboard.press("Escape")

    page.locator('//*[text()="Preview in Tabular Form"]').first.click()
    expect(page.locator('//div[text()="58001"]').first).to_be_visible()
    page.locator('//*[text()="Upload Photometry"]').first.click()
    expect(
        page.locator('//*[contains(.,"Upload successful. Your upload ID is")]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_csv_multiple_groups(
    page,
    sedm,
    super_admin_user_two_groups,
    public_group,
    public_group2,
    public_source_two_groups,
    super_admin_token,
):
    user = super_admin_user_two_groups
    public_source = public_source_two_groups
    inst_id = sedm.id
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/upload_photometry/{public_source.id}")
    page.locator('//textarea[@name="csvData"]').first.fill(CSV)

    page.locator('//*[@aria-labelledby="instrumentSelectLabel"]').first.click()
    page.locator(f'//li[@data-value="{inst_id}"]').first.click()
    page.keyboard.press("Escape")

    page.locator('//div[@id="selectGroups"]').first.click()
    page.locator(f'//li[@data-value="{public_group.id}"]').first.click()
    page.locator(f'//li[@data-value="{public_group2.id}"]').first.click()
    page.keyboard.press("Escape")

    page.locator('//*[text()="Preview in Tabular Form"]').first.click()
    expect(page.locator('//div[text()="58001"]').first).to_be_visible()
    page.locator('//*[text()="Upload Photometry"]').first.click()
    expect(
        page.locator('//*[contains(.,"Upload successful. Your upload ID is")]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_csv_with_altdata(
    page, sedm, super_admin_user, public_source, super_admin_token, public_group
):
    inst_id = sedm.id
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/upload_photometry/{public_source.id}")
    page.locator('//textarea[@name="csvData"]').first.fill(
        "mjd,flux,fluxerr,zp,magsys,filter,altdata.meta1,altdata.meta2\n"
        '58001,55,1,25,ab,sdssg,44.4,"abc,abc"\n'
        '58002,53,1,25,ab,sdssg,44.2,"edf,edf"'
    )

    page.locator('//*[@aria-labelledby="instrumentSelectLabel"]').first.click()
    page.locator(f'//li[@data-value="{inst_id}"]').first.click()
    page.keyboard.press("Escape")

    page.locator('//div[@id="selectGroups"]').first.click()
    page.locator(f'//li[@data-value="{public_group.id}"]').first.click()
    page.keyboard.press("Escape")

    page.locator('//*[text()="Preview in Tabular Form"]').first.click()
    expect(page.locator('//div[text()="58001"]').first).to_be_visible()
    page.locator('//*[text()="Upload Photometry"]').first.click()
    expect(
        page.locator('//*[contains(.,"Upload successful. Your upload ID is")]').first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_csv_form_validation(
    page, sedm, super_admin_user, public_source, super_admin_token, public_group
):
    inst_id = sedm.id
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/upload_photometry/{public_source.id}")
    csv_text_input = page.locator('//textarea[@name="csvData"]').first
    csv_text_input.fill(
        "mjd,flux,fluxerr,zp,magsys,OTHER\n58001,55,1,25,ab,sdssg\n58002,53,1,25,ab,sdssg"
    )
    page.locator('//*[text()="Preview in Tabular Form"]').first.click()
    expect(
        page.locator(
            '//div[contains(.,"Invalid input: Missing required column: filter")]'
        ).first
    ).to_be_visible()
    csv_text_input.fill(
        "mjd,flux,fluxerr,zp,magsys,filter\n58001,55,1,25,ab,sdssg\n58002,53,1,25,ab"
    )
    expect(
        page.locator(
            '//div[contains(.,"Invalid input: All data rows must have the same number of columns as header row")]'
        ).first
    ).to_be_visible()
    csv_text_input.fill("mjd,flux,fluxerr,zp,magsys,filter")
    expect(
        page.locator(
            '//div[contains(.,"Invalid input: There must be a header row and one or more data rows")]'
        ).first
    ).to_be_visible()
    csv_text_input.fill(CSV)
    expect(
        page.locator('//div[contains(.,"Select an instrument")]').first
    ).to_be_visible()

    page.locator('//*[@aria-labelledby="instrumentSelectLabel"]').first.click()
    page.locator(f'//li[@data-value="{inst_id}"]').first.click()
    page.keyboard.press("Escape")

    page.locator('//div[@id="selectGroups"]').first.click()
    page.locator(f'//li[@data-value="{public_group.id}"]').first.click()
    page.keyboard.press("Escape")

    page.locator('//*[text()="Preview in Tabular Form"]').first.click()
    expect(page.locator('//div[text()="58001"]').first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_form(page, sedm, super_admin_user, public_source):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/upload_photometry/{public_source.id}")

    page.locator('//*[contains(text(), "Using Form (one)")]').first.click()

    # instrument select
    page.locator('//*[@aria-labelledby="instrumentSelectLabel"]').first.click()
    page.locator(f'//li[@data-value="{sedm.id}"]').first.click()
    expect(page.locator(f'//li[@data-value="{sedm.id}"]').first).to_be_hidden()

    page.locator('//*[@id="root_group_ids"]').first.click()
    page.locator('//*[@aria-labelledby="root_group_ids-label"]/li[1]').first.click()
    page.keyboard.press("Escape")
    expect(
        page.locator('//*[@aria-labelledby="root_group_ids-label"]/li[1]').first
    ).to_be_hidden()

    page.locator('//*[@id="root_obsdate"]').first.fill("2017-05-09T12:34:56")
    page.locator('//*[@id="root_mag"]').first.fill("12.3")
    page.locator('//*[@id="root_magerr"]').first.fill("0.1")
    page.locator('//*[@id="root_limiting_mag"]').first.fill("20.0")
    page.locator('//*[@id="root_origin"]').first.fill("test")
    page.locator('//*[@id="root_nb_exposure"]').first.fill("6")
    page.locator('//*[@id="root_exposure_time"]').first.fill("60")

    page.locator('//*[@id="root_coordinates"]').first.click()
    page.locator('//*[@id="root_ra"]').first.fill("10.625")
    page.locator('//*[@id="root_dec"]').first.fill("41.2")

    page.locator('//*[@id="root_filter"]').first.click()
    page.locator('//*[text()="sdssg"]').first.click()

    page.locator('//*[text()="Submit"]').first.click()
    expect(
        page.locator('//*[contains(text(), "Photometry added successfully")]').first
    ).to_be_visible()
