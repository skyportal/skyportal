import os
import pytest

from skyportal.tests.utility_functions import load_gcnevent


@pytest.mark.flaky(reruns=2)
def test_recent_gcnevents(driver, user, super_admin_token):

    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    load_gcnevent(datafile, super_admin_token)

    driver.get(f'/become_user/{user.id}')
    driver.get('/')

    driver.wait_for_xpath('//*[text()="180116 00:36:53"]')
    driver.wait_for_xpath('//*[text()="Fermi"]')
    driver.wait_for_xpath('//*[text()="GRB"]')
