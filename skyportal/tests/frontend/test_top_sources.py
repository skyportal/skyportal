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
    # Wait for just added source to show up in added sources
    recent_source_class = "static-js-components-RecentSources__recentSourceItem"
    driver.wait_for_xpath(f'//div[contains(@class, "{recent_source_class}")]')

    # Test that front-end views register as source views
    driver.get(f'/source/{obj_id}')
    driver.wait_for_xpath(f'//div[text()="{obj_id}"]')
    driver.get('/')
    top_source_class = "static-js-components-TopSources__topSource"
    driver.wait_for_xpath(f'//div[contains(@class, "{top_source_class}")]')
    driver.wait_for_xpath("//*[contains(.,'1\u00a0view(s)')]")

    # Test that token requests are registered as source views
    status, data = api('GET', f'sources/{obj_id}', token=upload_data_token)
    assert status == 200
    driver.refresh()
    driver.wait_for_xpath("//*[contains(.,'2\u00a0view(s)')]")
