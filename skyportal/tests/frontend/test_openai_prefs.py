import uuid

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_openai_prefs(page, user, upload_data_token):
    page.goto(f"/become_user/{user.id}")
    page.goto("/profile")
    openai_toggle = page.locator('[data-testid="OpenAI_toggle"]').first
    expect(openai_toggle).to_be_visible()

    if not openai_toggle.is_checked():
        openai_toggle.click()

    dummy_api_key = f"sk-{uuid.uuid4()}"
    page.locator('//input[@name="openai_apikey"]').first.fill(dummy_api_key)

    page.locator('[data-testid="UpdateOpenAI"]').first.click()

    dummy_gpt_model = f"gpt-{uuid.uuid4()}"
    # rjsf's controlled input ignores fill(); select-all + type so React's
    # onChange fires and the form state actually updates.
    model_input = page.locator('//input[@name="root_model"]').first
    model_input.click()
    model_input.press("ControlOrMeta+a")
    model_input.press_sequentially(dummy_gpt_model)

    page.locator(
        "//form[@class='rjsf']//button[normalize-space()='Submit']"
    ).first.click()
    expect(page.locator("div.MuiDialog-container").first).to_be_hidden()

    status, data = api("GET", "internal/profile", token=upload_data_token)
    assert status == 200
    assert data["data"]["preferences"]["summary"]["OpenAI"]["model"] == dummy_gpt_model
    assert data["data"]["preferences"]["summary"]["OpenAI"]["apikey"] == dummy_api_key
    assert data["data"]["preferences"]["summary"]["OpenAI"]["active"]

    # uncheck the toggle
    page.locator('[data-testid="OpenAI_toggle"]').first.click()

    status, data = api("GET", "internal/profile", token=upload_data_token)
    assert status == 200
    assert not data["data"]["preferences"]["summary"]["OpenAI"]["active"]
