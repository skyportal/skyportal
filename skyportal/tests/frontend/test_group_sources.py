import uuid

from .. import api
from selenium.common.exceptions import TimeoutException


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

    # go to the group sources page
    driver.get(f"/group_sources/{public_group.id}")

    # find the name of the newly added source
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{obj_id}')]")

    # little triangle you push to expand the table
    expand_button = driver.wait_for_xpath("//*[@id='expandable-button']")
    driver.scroll_to_element_and_click(expand_button)

    # make sure the div containing the individual source appears
    driver.wait_for_xpath("//div[@class='MuiGrid-root MuiGrid-item']")

    try:  # the vega plot may take some time to appear, and in the meanwhile the MUI drawer gets closed for some reason.
        driver.wait_for_xpath(
            "//*[@class='vega-embed']"
        )  # make sure the table row opens up and show the vega plot
    except TimeoutException:
        # try again to click this triangle thingy to open the drawer
        expand_button = driver.wait_for_xpath("//*[@id='expandable-button']")
        driver.scroll_to_element_and_click(expand_button)

        # with the drawer opened again, it should now work...
        driver.wait_for_xpath(
            "//*[@class='vega-embed']"
        )  # make sure the table row opens up and show the vega plot
