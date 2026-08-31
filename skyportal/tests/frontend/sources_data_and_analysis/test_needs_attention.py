"""The home page's standing to-do list.

Notifications fire once and scroll away; an unanswered request is state, not an
event. This widget is where that state stays visible.
"""

from playwright.sync_api import expect


def test_the_widget_says_when_nothing_is_waiting(page, super_admin_user):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/")
    expect(page.locator('//h6[text()="Needs your attention"]').first).to_be_visible()
    expect(page.get_by_text("Nothing waiting on you.").first).to_be_visible()
