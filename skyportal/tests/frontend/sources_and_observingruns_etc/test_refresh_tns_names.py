"""The bulk TNS name refresh button on the sources page.

The tns_retrieval_queue service is disabled under test_config.yaml, so these
stop at the point where the request would hand a batch to the queue.
"""

from playwright.sync_api import expect


def open_dialog(page, user_id):
    page.goto(f"/become_user/{user_id}")
    page.goto("/sources")
    page.locator("[data-testid='refreshTNSNamesButton']").first.click()


def test_the_button_explains_what_it_refreshes(page, super_admin_user):
    open_dialog(page, super_admin_user.id)
    expect(page.locator("//*[text()='Refresh TNS names']").first).to_be_visible()
    expect(page.get_by_text("still carries the AT prefix")).to_be_visible()


def test_the_dialog_caps_how_many_sources_a_pass_takes(page, super_admin_user):
    open_dialog(page, super_admin_user.id)
    expect(page.get_by_label("Most sources to refresh")).to_have_value("100")


def test_a_user_who_cannot_manage_sources_is_not_offered_the_button(page, user):
    """The endpoint requires Manage sources, so the button stays hidden."""
    page.goto(f"/become_user/{user.id}")
    page.goto("/sources")
    expect(page.locator("[data-testid='refreshTNSNamesButton']")).to_have_count(0)
