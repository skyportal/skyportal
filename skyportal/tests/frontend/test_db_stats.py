def test_db_stats_page_render(
    driver, super_admin_user, public_group, public_source, public_candidate
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/db_stats")
    driver.wait_for_xpath('//*[text()="Number of candidates"]')
