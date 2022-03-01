import uuid
from skyportal.tests import api
from skyportal.model_util import create_token


def test_add_remove_favorites(driver, user, public_source):

    driver.get(f"/become_user/{user.id}")

    # go to source page, wait until it finishes loading
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath('//span[contains(text(), "Fe III")]', timeout=20)

    # make sure an empty favorites button appears (exclude) then click it!
    driver.click_xpath(f'//*[@data-testid="favorites-exclude_{public_source.id}"]')

    # make sure a filled favorites button appears (include) that means it was added successfully
    driver.wait_for_xpath(f'//*[@data-testid="favorites-include_{public_source.id}"]')

    # go to the favorites page
    driver.get("/favorites")

    # find the name of the newly added source
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{public_source.id}')]")

    # little triangle you push to expand the table
    driver.click_xpath("//*[@id='expandable-button']")

    # click to un-save the source as favorite
    driver.click_xpath(f'//*[@data-testid="favorites-text-include_{public_source.id}"]')

    driver.wait_for_xpath(
        '//*[contains(text(), "No sources have been saved as favorites.")]'
    )


def test_add_favorites_from_api(driver, super_admin_user, public_group):

    token_id = create_token(
        ACLs=["Upload data"], user_id=super_admin_user.id, name=str(uuid.uuid4())
    )

    obj_id = str(uuid.uuid4())

    # upload a new source, saved to the public group
    status, data = api(
        'POST',
        'sources',
        data={
            'id': f'{obj_id}',
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 0.153,
            'altdata': {'simbad': {'class': 'RRLyr'}},
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=token_id,
    )
    assert status == 200
    assert data['data']['id'] == f'{obj_id}'

    status, data = api(
        'POST',
        'listing',
        data={
            'user_id': super_admin_user.id,
            'obj_id': obj_id,
            'list_name': 'favorites',
        },
        token=token_id,
    )

    assert status == 200

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the groups sources page
    driver.get(f"/group_sources/{public_group.id}")

    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    driver.click_xpath("//input[@name='sourceID']")
    driver.wait_for_xpath("//input[@name='sourceID']").send_keys(obj_id)

    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']",
        scroll_parent=True,
    )
    # find the name of the newly added source
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{obj_id}')]")

    # click the filled star to un-save this source
    driver.click_xpath(f'//*[@data-testid="favorites-include_{obj_id}"]')

    # back to the favorites table
    driver.get("/favorites")

    # make sure there are no saved sources now
    driver.wait_for_xpath(
        '//*[contains(text(), "No sources have been saved as favorites.")]'
    )


def test_remove_favorites_from_api(driver, super_admin_user, public_group):

    token_id = create_token(
        ACLs=["Upload data"], user_id=super_admin_user.id, name=str(uuid.uuid4())
    )

    obj_id = str(uuid.uuid4())

    # upload a new source, saved to the public group
    status, data = api(
        'POST',
        'sources',
        data={
            'id': f'{obj_id}',
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 0.153,
            'altdata': {'simbad': {'class': 'RRLyr'}},
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=token_id,
    )
    assert status == 200
    assert data['data']['id'] == f'{obj_id}'

    status, data = api(
        'POST',
        'listing',
        data={
            'user_id': super_admin_user.id,
            'obj_id': obj_id,
            'list_name': 'favorites',
        },
        token=token_id,
    )

    assert status == 200
    listing_id = data["data"]["id"]

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the favorites page
    driver.get("/favorites")

    # find the name of the newly added source
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{obj_id}')]", timeout=20)

    # remove this listing via API
    status, data = api(
        'DELETE',
        f'listing/{listing_id}',
        token=token_id,
    )

    assert status == 200

    # refresh the page to see the source is gone
    driver.get("/favorites")

    # make sure there are no saved sources now
    driver.wait_for_xpath(
        '//*[contains(text(), "No sources have been saved as favorites.")]'
    )
