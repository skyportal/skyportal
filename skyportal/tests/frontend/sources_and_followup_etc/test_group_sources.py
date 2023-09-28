import uuid
import pytest
from skyportal.tests import api

from tdtax import taxonomy, __version__
from datetime import datetime, timezone


@pytest.mark.flaky(reruns=2)
def test_add_new_source_renders_on_group_sources_page(
    driver,
    super_admin_user_two_groups,
    public_group,
    public_group2,
    upload_data_token_two_groups,
    taxonomy_token_two_groups,
    classification_token_two_groups,
):

    driver.get(f"/become_user/{super_admin_user_two_groups.id}")  # become a super-user

    # go to the group sources page
    driver.get(f"/group_sources/{public_group.id}")

    # make sure the group name appears
    driver.wait_for_xpath(f"//*[text()[contains(., '{public_group.name}')]]")

    # make a new object/source and save the time when it was posted
    obj_id = str(uuid.uuid4())
    t0 = datetime.now(timezone.utc)

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
            'group_ids': [public_group.id, public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data['data']['id'] == f'{obj_id}'

    # need to reload the page to see changes!
    driver.get(f"/group_sources/{public_group.id}")

    # find the name of the newly added source
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{obj_id}')]")

    # find the date it was saved
    driver.wait_for_xpath(
        f"//*[text()[contains(., '{t0.strftime('%Y-%m-%dT%H:%M')}')]]"
    )

    # check the redshift shows up
    driver.wait_for_xpath(f"//*[text()[contains(., '{'0.153'}')]]")

    # little triangle you push to expand the table
    driver.click_xpath("//*[@id='expandable-button']")

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

    # check the classification does show up
    driver.wait_for_xpath(f"//*[text()[contains(., '{'Algol'}')]]")

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
    # ensure new classification is displayed
    driver.wait_for_xpath(f"//*[text()[contains(., '{'RS CVn'}')]]")

    # ensure other classification is still displayed
    driver.wait_for_xpath(f"//*[text()[contains(., '{'Algol'}')]]")


def test_request_source(
    driver,
    super_admin_user_two_groups,
    public_group,
    public_group2,
    upload_data_token,
    upload_data_token_two_groups,
):

    driver.get(f"/become_user/{super_admin_user_two_groups.id}")  # become a super-user

    # go to the group sources page
    driver.get(f"/group_sources/{public_group.id}")

    # make sure the group name appears
    driver.wait_for_xpath(f"//*[text()[contains(., '{public_group.name}')]]")

    obj_id = str(uuid.uuid4())

    # upload a new source, saved to public_group2
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

    # reload the group sources page
    driver.get(f"/group_sources/{public_group2.id}")

    # there should not be any new sources (the source is in group1)
    driver.wait_for_xpath(
        f"//div[@data-testid='source_table_{public_group2.name} sources']//*[text()[contains(., 'Sorry, no matching records found')]]"
    )

    # request this source to be added to group2
    status, data = api(
        'POST',
        'source_groups',
        data={'objId': f'{obj_id}', 'inviteGroupIds': [public_group2.id]},
        token=upload_data_token,
    )
    assert status == 200

    # reload the group sources page
    driver.get(f"/group_sources/{public_group2.id}")

    # make sure the second table appears
    driver.wait_for_xpath("//*[text()[contains(., 'Requested to save')]]")

    # find the name of the newly added source
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{obj_id}')]")

    # make sure the second table has "save/ignore" buttons
    driver.wait_for_xpath("//*[text()[contains(., 'Save')]]")
    driver.wait_for_xpath("//*[text()[contains(., 'Ignore')]]")


def test_sources_sorting(
    driver,
    super_admin_user,
    public_group,
    upload_data_token,
):
    obj_id = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # upload two new sources, saved to the public group
    status, data = api(
        'POST',
        'sources',
        data={
            'id': f'{obj_id}',
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 0.0,
            'altdata': {'simbad': {'class': 'RRLyr'}},
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == f'{obj_id}'
    status, data = api(
        'POST',
        'sources',
        data={
            'id': f'{obj_id2}',
            'ra': 234.22,
            'dec': -22.33,
            'redshift': 0.153,
            'altdata': {'simbad': {'class': 'RRLyr'}},
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == f'{obj_id2}'

    driver.get(f"/become_user/{super_admin_user.id}")  # become a super-user

    # Go to the group sources page
    driver.get(f"/group_sources/{public_group.id}")

    # Wait for the group name appears
    driver.wait_for_xpath(f"//*[text()[contains(., '{public_group.name}')]]")

    # Now sort by date saved desc by clicking the header twice
    driver.click_xpath("//*[text()='Saved at']")
    driver.click_xpath("//*[text()='Saved at']")

    # Now, the first one posted should be the second row
    # Col 0, Row 0 should be the second sources's id (MuiDataTableBodyCell-0-0)
    driver.wait_for_xpath(
        f'//td[contains(@data-testid, "MuiDataTableBodyCell-0-0")][.//span[text()="{obj_id2}"]]'
    )
    # Col 0, Row 1 should be the first sources's id (MuiDataTableBodyCell-0-1)
    driver.wait_for_xpath(
        f'//td[contains(@data-testid, "MuiDataTableBodyCell-0-1")][.//span[text()="{obj_id}"]]'
    )

    # Now sort by redshift ascending, which would put obj_id first
    driver.click_xpath("//*[text()='Redshift']")

    # Now, the first one posted should be the second row
    # Col 0, Row 0 should be the second sources's id (MuiDataTableBodyCell-0-0)
    driver.wait_for_xpath(
        f'//td[contains(@data-testid, "MuiDataTableBodyCell-0-0")][.//span[text()="{obj_id}"]]'
    )
    # Col 0, Row 1 should be the first sources's id (MuiDataTableBodyCell-0-1)
    driver.wait_for_xpath(
        f'//td[contains(@data-testid, "MuiDataTableBodyCell-0-1")][.//span[text()="{obj_id2}"]]'
    )
