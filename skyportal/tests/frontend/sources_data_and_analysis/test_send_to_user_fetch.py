"""What the source page pulls from the user list.

Every consumer on a source page -- @-mention autocomplete, the redshift
history's "set by", the assignment requester -- needs only a name. The full
record carries each user's groups, roles and ACLs, which on a real instance is
megabytes. None of that belongs on the critical path of opening a source.
"""

from playwright.sync_api import expect


def user_list_requests(urls):
    return [url for url in urls if url.split("?")[0].endswith("/api/user")]


def test_a_source_page_never_fetches_the_full_user_list(
    page, super_admin_user, public_source
):
    requested = []
    page.on("request", lambda request: requested.append(request.url))

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")

    # The button existing means the sharing dialog is mounted -- the point at
    # which it used to fetch every user.
    send_to = page.locator('//button[normalize-space(text())="Send to"]').first
    expect(send_to).to_be_visible()

    for url in user_list_requests(requested):
        assert "slim=true" in url, f"source page fetched the full user list: {url}"


def test_the_sharing_dialog_fetches_users_only_when_opened(
    page, super_admin_user, public_source
):
    """It needs the full records, so it must wait until it is actually open."""
    requested = []
    page.on("request", lambda request: requested.append(request.url))

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")
    send_to = page.locator('//button[normalize-space(text())="Send to"]').first
    expect(send_to).to_be_visible()

    assert [u for u in user_list_requests(requested) if "slim=true" not in u] == [], (
        "the full user list was fetched before the dialog was opened"
    )

    # Arm the wait before clicking: the request can land before a later
    # listener starts.
    with page.expect_request(
        lambda request: (
            request.url.split("?")[0].endswith("/api/user")
            and "slim=true" not in request.url
        ),
        timeout=30000,
    ):
        send_to.click()
