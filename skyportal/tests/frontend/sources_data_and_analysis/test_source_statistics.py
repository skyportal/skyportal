from playwright.sync_api import expect


def test_source_statistics_object_id_search(page, super_admin_user, public_source):
    """Object-list mode: search-and-select, then freeSolo entry of unknown IDs."""
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/source_statistics")

    page.get_by_role("button", name="Object list").click()
    obj_ids = page.get_by_label("Object IDs")

    obj_ids.fill(public_source.id)
    page.get_by_role("option", name=public_source.id).first.click()
    expect(
        page.locator(".MuiChip-label", has_text=public_source.id).first
    ).to_be_visible()

    # Count, not text: one unsplit chip would contain both IDs.
    obj_ids.fill("ZTFnotreal1, ZTFnotreal2")
    obj_ids.press("Enter")
    expect(page.locator(".MuiChip-label")).to_have_count(3)
    expect(page.get_by_text("ZTFnotreal1", exact=True)).to_be_visible()
    expect(page.get_by_text("ZTFnotreal2", exact=True)).to_be_visible()
