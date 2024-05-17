import uuid
import pytest


@pytest.mark.flaky(reruns=5)
def test_analysis_service_frontend(
    super_admin_token, super_admin_user, analysis_service_token, view_only_user, driver
):
    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the analysis services page
    driver.get("/services")

    # add dropdown analysis
    analysis_name = str(uuid.uuid4())
    display_name = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(analysis_name)
    driver.wait_for_xpath('//*[@id="root_display_name"]').send_keys(display_name)
    driver.wait_for_xpath('//*[@id="root_url"]').send_keys(
        f"http://localhost:5000/analysis/{analysis_name}"
    )
    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check for analysis service
    driver.wait_for_xpath(f'//span[text()[contains(.,"{display_name}")]]', timeout=20)

    # check for user who can only view
    driver.get(f"/become_user/{view_only_user.id}")

    # go to the analysis services page
    driver.get("/services")

    # check for analysis service
    driver.wait_for_xpath(f'//span[text()[contains(.,"{display_name}")]]', timeout=20)

    # confirm that no submission
    driver.wait_for_xpath_to_disappear(submit_button_xpath)
