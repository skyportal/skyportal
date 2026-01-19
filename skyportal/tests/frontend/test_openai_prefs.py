import uuid

import pytest

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_openai_prefs(driver, user, upload_data_token):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    openai_toggle = driver.wait_for_xpath('//*[@data-testid="OpenAI_toggle"]')

    if not openai_toggle.is_selected():
        driver.scroll_to_element_and_click(openai_toggle)

    dummy_api_key = f"sk-{str(uuid.uuid4())}"

    apikey_input = driver.wait_for_xpath('//input[@name="openai_apikey"]')
    driver.scroll_to_element_and_click(apikey_input)
    apikey_input.send_keys(dummy_api_key)

    openai_prefs = driver.wait_for_xpath('//*[@data-testid="UpdateOpenAI"]')
    driver.scroll_to_element_and_click(openai_prefs)

    dummy_gpt_model = f"gpt-{str(uuid.uuid4())}"
    model_input = driver.wait_for_xpath('//input[@name="root_model"]')
    driver.scroll_to_element_and_click(model_input)
    model_input.clear()
    model_input.send_keys(dummy_gpt_model)

    driver.click_xpath(
        "//form[@class='rjsf']/div/button[text()='Submit']", scroll_parent=True
    )
    driver.wait_for_css_to_disappear("div.MuiDialog-container")

    openai_toggle = driver.wait_for_xpath('//*[@data-testid="OpenAI_toggle"]')

    status, data = api("GET", "internal/profile", token=upload_data_token)
    assert status == 200
    assert data["data"]["preferences"]["summary"]["OpenAI"]["model"] == dummy_gpt_model
    assert data["data"]["preferences"]["summary"]["OpenAI"]["apikey"] == dummy_api_key
    assert data["data"]["preferences"]["summary"]["OpenAI"]["active"]

    # uncheck the toggle
    driver.scroll_to_element_and_click(openai_toggle)

    status, data = api("GET", "internal/profile", token=upload_data_token)
    assert status == 200
    assert not data["data"]["preferences"]["summary"]["OpenAI"]["active"]
