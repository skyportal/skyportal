import pytest


@pytest.mark.flaky(reruns=2)
def test_recent_gcnevents(driver, user, super_admin_token, gcn_GRB):

    driver.get(f'/become_user/{user.id}')
    driver.get('/')

    driver.wait_for_xpath('//*[text()="180116 00:36:53"]')
    driver.wait_for_xpath('//*[text()="Fermi"]')
    driver.wait_for_xpath('//*[text()="GRB"]')
