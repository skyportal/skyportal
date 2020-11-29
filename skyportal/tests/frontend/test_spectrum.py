def test_delete_spectrum(driver, public_source):

    spectrum = public_source.spectra[0]
    driver.get(f"/become_user/{spectrum.owner_id}")
    driver.get(f"/source/{public_source.id}")

    # wait for plots to load
    driver.wait_for_xpath('//div[@class="bk-root"]//span[text()="Flux"]', timeout=20)
    # this waits for the spectroscopy plot by looking for the element Mg
    driver.wait_for_xpath('//div[@class="bk-root"]//label[text()="Mg"]', timeout=20)

    driver.click_xpath('//*[@data-testid="view-spectra-button"]')

    # wait for plots to load
    # this waits for the spectroscopy plot by looking for the element Mg
    driver.wait_for_xpath('//div[@class="bk-root"]//label[text()="Mg"]', timeout=20)

    driver.click_xpath("//*[@data-testid='delete-spectrum-button']")
    driver.click_xpath("//*[@data-testid='yes-delete']")

    driver.wait_for_xpath_to_disappear('//h5')
