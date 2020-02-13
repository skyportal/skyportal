import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By

from skyportal.tests import api


def test_news_feed(driver, user, public_source, public_group, upload_data_token, comment_token):
    source_id_base = str(uuid.uuid4())
    for i in range(2):
        status, data = api('POST', 'sources',
                           data={'id': f'{source_id_base}_{i}',
                                 'ra': 234.22,
                                 'dec': -22.33,
                                 'redshift': 3,
                                 'simbad_class': 'RRLyr',
                                 'transient': False,
                                 'ra_dis': 2.3,
                                 'group_ids': [public_group.id]},
                           token=upload_data_token)
        assert status == 200
        assert data['data']['id'] == f'{source_id_base}_{i}'

        status, data = api('POST', 'comment', data={'source_id': f'{source_id_base}_{i}',
                                                    'text': f'comment_text_{i}'},
                           token=comment_token)
        assert status == 200

    driver.get(f'/become_user/{user.id}')
    driver.get('/')
    driver.wait_for_xpath(f'//span[text()="a few seconds ago"]')
    for i in range(2):
        driver.wait_for_xpath(f'//span[text()="New source {source_id_base}_{i}"]')
        driver.wait_for_xpath(f'//span[contains(text(),"comment_text_{i} ({source_id_base}_{i})")]')
