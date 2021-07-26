import uuid

from skyportal.tests import api
from tdtax import taxonomy, __version__

from datetime import datetime, timezone, timedelta

from dateutil import parser


def test_add_sources_two_groups(
    driver,
    super_admin_user_two_groups,
    public_group,
    public_group2,
    upload_data_token_two_groups,
    taxonomy_token_two_groups,
    classification_token_two_groups,
):
    obj_id = str(uuid.uuid4())
    t1 = datetime.now(timezone.utc)

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
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data['data']['id'] == f'{obj_id}'

    driver.get(
        f"/become_user/{super_admin_user_two_groups.id}"
    )  # TODO decorator/context manager?
    assert 'localhost' in driver.current_url
    driver.get('/sources')

    # filter on the object id
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")

    obj_button = driver.wait_for_xpath("//input[@name='sourceID']")
    obj_button.clear()
    obj_button.send_keys(obj_id)
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']"
    )

    # find the name of the newly added source
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{obj_id}')]")

    # find the date it was saved
    saved_at_element = driver.wait_for_xpath(
        f"//*[text()[contains(., '{t1.strftime('%Y-%m-%dT%H:%M')}')]]"
    )
    saved_group1 = parser.parse(saved_at_element.text + " UTC")
    assert abs(saved_group1 - t1) < timedelta(seconds=30)

    # check the redshift shows up
    driver.wait_for_xpath(f"//*[text()[contains(., '{'0.153'}')]]")

    # little triangle you push to expand the table
    driver.click_xpath(
        "//tr[@data-testid='MUIDataTableBodyRow-0']//*[@id='expandable-button']"
    )

    # make sure the div containing the individual source appears
    driver.wait_for_xpath(f'//tr[@data-testid="groupSourceExpand_{obj_id}"]')

    # post a taxonomy and classification
    status, data = api(
        'POST',
        'taxonomy',
        data={
            'name': "test taxonomy" + str(uuid.uuid4()),
            'hierarchy': taxonomy,
            'group_ids': [public_group.id, public_group2.id],
            'provenance': f"tdtax_{__version__}",
            'version': __version__,
            'isLatest': True,
        },
        token=taxonomy_token_two_groups,
    )
    assert status == 200
    taxonomy_id = data['data']['taxonomy_id']

    status, data = api(
        'POST',
        'classification',
        data={
            'obj_id': obj_id,
            'classification': 'Algol',
            'taxonomy_id': taxonomy_id,
            'probability': 1.0,
            'group_ids': [public_group.id],
        },
        token=classification_token_two_groups,
    )
    assert status == 200

    # check the classification doesn't shows up (it should not show up without a page refresh!)
    driver.wait_for_xpath_to_disappear(
        f"//*[text()[contains(., '{'Algol'}')]]", timeout=1
    )

    # filter on the object id (page refresh, but still filtering on this object)
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    obj_button = driver.wait_for_xpath("//input[@name='sourceID']")
    obj_button.clear()
    obj_button.send_keys(obj_id)
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']"
    )

    # check the classification does show up after a refresh
    driver.wait_for_xpath(f"//*[text()[contains(., '{'Algol'}')]]")

    # add this source to another group
    t2 = datetime.now(timezone.utc)
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
            'group_ids': [public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data['status'] == 'success'

    # post another classification, by another group
    status, data = api(
        'POST',
        'classification',
        data={
            'obj_id': obj_id,
            'classification': 'RS CVn',
            'taxonomy_id': taxonomy_id,
            'probability': 1.0,
            'group_ids': [public_group2.id],
        },
        token=classification_token_two_groups,
    )
    assert status == 200

    # filter on the object id (page refresh, but still filtering on this object)
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    obj_button = driver.wait_for_xpath("//input[@name='sourceID']")
    obj_button.clear()
    obj_button.send_keys(obj_id)
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']"
    )

    # make sure the new classification, made to group 2, shows up
    driver.wait_for_xpath(f"//*[text()[contains(., '{'RS CVn'}')]]")

    # find the date it was saved to group2
    saved_at_element = driver.wait_for_xpath(
        f"//*[text()[contains(., '{t2.strftime('%Y-%m-%dT%H:%M')}')]]"
    )
    saved_group2 = parser.parse(saved_at_element.text + " UTC")
    assert abs(saved_group2 - t2) < timedelta(seconds=2)

    # the new group must have been saved later!
    assert saved_group2 > saved_group1


def test_filter_by_classification(
    driver,
    user,
    public_group,
    upload_data_token,
    taxonomy_token,
    classification_token,
):
    # Post an object with a classification
    source_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": source_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    taxonomy_name = "test taxonomy" + str(uuid.uuid4())
    status, data = api(
        'POST',
        'taxonomy',
        data={
            'name': taxonomy_name,
            'hierarchy': taxonomy,
            'group_ids': [public_group.id],
            'provenance': f"tdtax_{__version__}",
            'version': __version__,
            'isLatest': True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data['data']['taxonomy_id']

    status, data = api(
        'POST',
        'classification',
        data={
            'obj_id': source_id,
            'classification': 'Algol',
            'taxonomy_id': taxonomy_id,
            'probability': 1.0,
            'group_ids': [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/sources")

    # Filter for classification
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    driver.click_xpath(
        "//div[@data-testid='classifications-select']",
        scroll_parent=True,
    )
    driver.click_xpath(
        f"//li[@data-value='{taxonomy_name}: Algol']", scroll_parent=True
    )
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']"
    )

    # Should see the posted source
    driver.wait_for_xpath(f'//a[@data-testid="{source_id}"]')

    # Now search for a different classification
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    driver.click_xpath(
        "//div[@data-testid='classifications-select']",
        scroll_parent=True,
    )
    driver.click_xpath(f"//li[@data-value='{taxonomy_name}: AGN']", scroll_parent=True)
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']"
    )
    # Should no longer see the source
    driver.wait_for_xpath_to_disappear(f'//a[@data-testid="{source_id}"]')


def test_filter_by_alias_and_origin(
    driver,
    user,
    public_group,
    upload_data_token,
    taxonomy_token,
    classification_token,
):
    # Post an object with an alias and an origin
    source_id = str(uuid.uuid4())
    alias = str(uuid.uuid4())
    origin = str(uuid.uuid4())

    status, data = api(
        "POST",
        "sources",
        data={
            "id": source_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
            "alias": [alias],
            "origin": origin,
        },
        token=upload_data_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/sources")

    # Filter for alias
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    alias_field = driver.wait_for_xpath(
        "//*[@data-testid='alias-text']//input",
    )

    alias_field.send_keys(alias)
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']",
        scroll_parent=True,
    )

    # Should see the posted source
    driver.wait_for_xpath(f'//a[@data-testid="{source_id}"]')

    # Now search for a different alias
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    alias_field = driver.wait_for_xpath("//*[@data-testid='alias-text']//input")
    alias_field.send_keys(str(uuid.uuid4()))
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']"
    )

    # Should no longer see the source
    driver.wait_for_xpath_to_disappear(f'//a[@data-testid="{source_id}"]')

    # Filter for origin
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    alias_field = driver.wait_for_xpath(
        "//*[@data-testid='origin-text']//input",
    )
    alias_field.send_keys(origin)
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']"
    )

    # Should see the posted source
    driver.wait_for_xpath(f'//a[@data-testid="{source_id}"]')

    # Now search for a different alias
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    origin_field = driver.wait_for_xpath(
        "//*[@data-testid='origin-text']//input",
    )
    origin_field.send_keys(str(uuid.uuid4()))
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']"
    )

    # Should no longer see the source
    driver.wait_for_xpath_to_disappear(f'//a[@data-testid="{source_id}"]')


def test_hr_diagram(
    driver,
    user,
    public_group,
    upload_data_token,
    annotation_token,
):

    # Post an object with Gaia data
    source_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": source_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")

    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': source_id,
            'origin': 'cross_match1',
            'data': {
                'gaia': {'Mag_G': 11.3, 'Mag_Bp': 11.8, 'Mag_Rp': 11.0, 'Plx': 20},
            },
        },
        token=annotation_token,
    )
    assert status == 200

    driver.get("/sources")

    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    obj_button = driver.wait_for_xpath("//input[@name='sourceID']")
    obj_button.clear()
    obj_button.send_keys(source_id)
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']"
    )

    # find the name of the newly added source
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{source_id}')]")

    # little triangle you push to expand the table
    driver.click_xpath("//*[@id='expandable-button']")

    # make sure the div containing the individual source appears
    driver.wait_for_xpath(f'//tr[@data-testid="groupSourceExpand_{source_id}"]')

    driver.wait_for_xpath(f'//div[@data-testid="hr_diagram_{source_id}"]')
