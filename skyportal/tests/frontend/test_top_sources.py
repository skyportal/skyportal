import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By

from skyportal.tests import api


def test_top_sources(driver, user, public_source, public_group, upload_data_token):
    source_id = str(uuid.uuid4())
    status, data = api('POST', 'sources',
                       data={'id': source_id,
                             'ra': 50.4,
                             'dec': 22.33,
                             'redshift': 2.1,
                             'simbad_class': 'RRLyr',
                             'transient': False,
                             'ra_dis': 2.3,
                             'group_ids': [public_group.id]},
                       token=upload_data_token)
    assert status == 200
    assert data['data']['id'] == source_id

    driver.get(f'/become_user/{user.id}')
    driver.get('/')
    driver.wait_for_xpath(f'//td[text()="RRLyr"]')
    driver.wait_for_xpath_to_disappear(f'//em[contains(.,"views)")]')
    driver.get(f'/source/{source_id}')
    driver.wait_for_xpath(f'//div[text()="{source_id}"]')
    driver.get('/')
    driver.wait_for_xpath(f'//td[text()="RRLyr"]')
    driver.wait_for_xpath(f'//*[contains(.,"views)")]')
