import arrow
from selenium.webdriver.common.by import By


def test_db_stats_page_render(
    driver, super_admin_user, public_group, public_source, public_candidate
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/db_stats")
    driver.wait_for_xpath('//*[text()="Number of candidates"]')
    oldest_cand_em = driver.wait_for_xpath(
        '//*[text()="Oldest candidate creation datetime"]'
    )
    oldest_cand_row = oldest_cand_em.find_element(By.XPATH, "../..")
    created_at_td = oldest_cand_row.find_elements(By.XPATH, ".//td")[-1]
    arrow.get(created_at_td.text)
