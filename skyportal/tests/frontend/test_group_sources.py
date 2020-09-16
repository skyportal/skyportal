import uuid

# import pytest
# from ...models import DBSession
from .. import api

import time


def test_add_new_source(driver, super_admin_user, public_group, upload_data_token):

    obj_id = str(uuid.uuid4())

    driver.get(f"/become_user/{super_admin_user.id}")  # become a super-user

    # upload a new source, saved to the public group
    status, data = api(
        'POST',
        'sources',
        data={
            'id': f'{obj_id}',
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 3,
            'altdata': {'simbad': {'class': 'RRLyr'}},
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == f'{obj_id}'

    driver.get(f"/source/{obj_id}")
    time.sleep(10)
    # driver.save_screenshot('test_source_page.png')

    driver.get(f"/group_sources/{public_group.id}")  # go to the group sources page

    # driver.save_screenshot('test_group_page.png')

    driver.wait_for_xpath(
        f"//a[contains(@href, '/source/{obj_id}')]"
    )  # find the name of the newly added source

    expand_button = driver.wait_for_xpath(
        "//*[@id='expandable-button']"
    )  # little triangle you push to expand the table
    driver.scroll_to_element_and_click(expand_button)

    driver.save_screenshot('test_open_drawer.png')

    driver.wait_for_xpath(
        "//*[@class='vega-embed']"
    )  # make sure the table row opens up and show the vega plot
