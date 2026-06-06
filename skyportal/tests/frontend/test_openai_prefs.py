import time
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
    # onChange fires and the form state actually updates. Wait for the form to
    # finish populating its default model first -- typing before that races the
    # async default-set, leaving the field (and saved prefs) wrong.
    model_input = page.locator('//input[@name="root_model"]').first
    expect(model_input).not_to_have_value("")
    model_input.click()
    model_input.press("ControlOrMeta+a")
    model_input.press("Delete")
    model_input.press_sequentially(dummy_gpt_model)
    expect(model_input).to_have_value(dummy_gpt_model)

    page.locator(
        "//form[@class='rjsf']//button[normalize-space()='Submit']"
    ).first.click()
    expect(page.locator("div.MuiDialog-container").first).to_be_hidden()

    # The preference save is async (the dialog closes optimistically), so poll
    # the profile until the model lands rather than racing the GET.
    openai = {}
    for _ in range(20):
        status, data = api("GET", "internal/profile", token=upload_data_token)
        assert status == 200
        openai = data["data"]["preferences"].get("summary", {}).get("OpenAI", {})
        if openai.get("model") == dummy_gpt_model:
            break
        time.sleep(0.5)
    assert openai.get("model") == dummy_gpt_model
    assert openai.get("apikey") == dummy_api_key
    assert openai.get("active")

    # uncheck the toggle
    page.locator('[data-testid="OpenAI_toggle"]').first.click()

    status, data = api("GET", "internal/profile", token=upload_data_token)
    assert status == 200
    assert not data["data"]["preferences"]["summary"]["OpenAI"]["active"]
