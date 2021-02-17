import arrow


def test_db_stats_page_render(
    driver, user, public_group, public_source, public_candidate
):
    driver.get(f"/become_user/{user.id}")
    driver.get("/db_stats")
    driver.wait_for_xpath('//*[text()="numCandidates"]')
    oldest_cand_em = driver.wait_for_xpath('//*[text()="oldestCandidateCreatedAt"]')
    oldest_cand_row = oldest_cand_em.find_element_by_xpath("../..")
    created_at_td = oldest_cand_row.find_elements_by_xpath("//td")[-1]
    arrow.get(created_at_td.text)
