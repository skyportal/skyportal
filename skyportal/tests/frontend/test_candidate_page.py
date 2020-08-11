def test_public_candidate_page_render(driver, user, public_candidate):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/candidate/{public_candidate.id}")
    driver.wait_for_xpath(f'//div[text()="{public_candidate.id}"]')
    driver.wait_for_xpath(
        '//label[contains(text(), "band")]'
    )  # TODO how to check plot?
    driver.wait_for_xpath('//label[contains(text(), "Fe III")]')
