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

    driver.get(
        f"/become_user/{super_admin_user_two_groups.id}"
    )  # TODO decorator/context manager?
    assert 'localhost' in driver.current_url
    driver.get('/sources')
    driver.wait_for_xpath('//h6[contains(text(), "Sources")]')

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

    # filter on the object id
    obj_button = driver.wait_for_xpath("//input[@name='sourceID']")
    obj_button.clear()
    obj_button.send_keys(obj_id)
    submit = "//button[contains(.,'Submit')]"
    driver.click_xpath(submit)

    # find the name of the newly added source
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{obj_id}')]")

    # find the date it was saved
    saved_at_element = driver.wait_for_xpath(
        f"//*[text()[contains(., '{t1.strftime('%Y-%m-%dT%H:%M')}')]]"
    )
    saved_group1 = parser.parse(saved_at_element.text + " UTC")
    assert abs(saved_group1 - t1) < timedelta(seconds=2)

    # check the redshift shows up
    driver.wait_for_xpath(f"//*[text()[contains(., '{'0.153'}')]]")

    # little triangle you push to expand the table
    driver.click_xpath("//*[@id='expandable-button']")

    # make sure the div containing the individual source appears
    driver.wait_for_xpath(f'//tr[@data-testid="groupSourceExpand_{obj_id}"]')

    driver.wait_for_xpath("//*[@class='vega-embed']")

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

    # making sure the drawer is still open even after posting a classification!
    driver.wait_for_xpath("//*[@class='vega-embed']")

    # filter on the object id (page refresh, but still filtering on this object)
    obj_button = driver.wait_for_xpath("//input[@name='sourceID']")
    obj_button.clear()
    obj_button.send_keys(obj_id)
    submit = "//button[contains(.,'Submit')]"
    driver.click_xpath(submit)

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
    obj_button = driver.wait_for_xpath("//input[@name='sourceID']")
    obj_button.clear()
    obj_button.send_keys(obj_id)
    submit = "//button[contains(.,'Submit')]"
    driver.click_xpath(submit)

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
