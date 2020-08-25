import uuid

from skyportal.tests import api


def test_top_sources(driver, user, public_source, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': 50.4,
            'dec': 22.33,
            'redshift': 2.1,
            "altdata": {"simbad": {"class": "RRLyr"}},
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    driver.get(f'/become_user/{user.id}')
    driver.get('/')
    driver.wait_for_xpath(f'//a[text()="{obj_id}"]')

    # Test that front-end views register as source views
    driver.click_xpath(f'//a[text()="{obj_id}"]')
    driver.wait_for_xpath(f'//div[text()="{obj_id}"]')
    driver.click_xpath('//span[text()="Dashboard"]')
    driver.wait_for_xpath(f'//*[contains(.,"1 view(s)")]')

    # Test that token requests are registered as source views
    status, data = api('GET', f'sources/{obj_id}', token=upload_data_token)
    assert status == 200
    driver.wait_for_xpath(f'//*[contains(.,"2 view(s)")]')
