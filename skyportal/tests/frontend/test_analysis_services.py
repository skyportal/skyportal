import time
import uuid

import pytest


@pytest.mark.flaky(reruns=2)
def test_analysis_service_frontend(
    super_admin_token, super_admin_user, analysis_service_token, view_only_user, driver
):
    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the analysis services page
    driver.get("/services")

    # add dropdown analysis
    analysis_name = str(uuid.uuid4())
    display_name = str(uuid.uuid4())

    add_button = driver.wait_for_xpath('//button[@name="new_analysis_service"]')
    add_button.click()

    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(analysis_name)
    driver.wait_for_xpath('//*[@id="root_display_name"]').send_keys(display_name)
    driver.wait_for_xpath('//*[@id="root_url"]').send_keys(
        f"http://localhost:5000/analysis/{analysis_name}"
    )

    n_retries = 0
    while n_retries < 10:
        try:
            submit_button = driver.wait_for_xpath('//button[@type="submit"]')
            # scroll down the MUI dialog to make the submit button clickable
            driver.execute_script("arguments[0].scrollIntoView();", submit_button)
            submit_button.click()
            break
        except Exception:
            n_retries += 1
            time.sleep(1)
            continue

    if n_retries == 10:
        raise Exception('Failed to click submit button')

    # check for analysis service
    driver.wait_for_xpath(f'//td/div[contains(.,"{display_name}")]', timeout=20)

    # check for user who can only view
    driver.get(f"/become_user/{view_only_user.id}")

    # go to the analysis services page
    driver.get("/services")

    # check for analysis service
    driver.wait_for_xpath(f'//td/div[contains(.,"{display_name}")]', timeout=20)

    # confirm that no submission without permission
    driver.wait_for_xpath_to_disappear('//button[@name="new_analysis_service"]')
