import uuid

import pytest
from playwright.sync_api import expect


@pytest.mark.flaky(reruns=2)
def test_submit_and_delete_new_assignment(
    page, super_admin_user, public_source, red_transients_run
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")

    page.locator(
        '//*[@role="combobox" and (@aria-labelledby="assignmentSelect" or @id="assignmentSelect")]'
    ).first.click()
    observingrun_title = (
        f"{red_transients_run.calendar_date} "
        f"{red_transients_run.instrument.name}/"
        f"{red_transients_run.instrument.telescope.nickname} "
        f"(PI: {red_transients_run.pi} / "
        f"Group: {red_transients_run.group.name})"
    )
    expect(page.locator(f'//*[text()="{observingrun_title}"]').first).to_be_visible()
    page.locator(f'//li[@data-value="{red_transients_run.id}"]').first.click()
    page.keyboard.press("Escape")

    comment_text = str(uuid.uuid4())
    page.locator("//textarea[@name='comment']").first.fill(comment_text)

    page.locator('//*[@name="assignmentSubmitButton"]').first.click()
    expect(page.locator(f'//*[text()="{comment_text}"]').first).to_be_visible()

    # delete the assignment
    page.locator('//*[starts-with(@id, "delete_button_assignment_")]').first.click()
    page.locator("//*[contains(text(), 'Confirm')]").first.click()
    expect(page.locator(f'//*[text()="{comment_text}"]').first).to_be_hidden()
