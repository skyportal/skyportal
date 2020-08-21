import uuid
import pytest

from skyportal.tests import api


def test_source_list(driver, user, public_source, private_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    assert 'localhost' in driver.current_url
    driver.get('/sources')

    simbad_class = public_source.altdata['simbad']['class']
    driver.wait_for_xpath('//h2[contains(text(), "Sources")]')
    driver.wait_for_xpath(f'//a[text()="{public_source.id}"]')
    driver.wait_for_xpath(f'//td[text()="{simbad_class}"]')
    driver.wait_for_xpath_to_disappear(f'//a[text()="{private_source.id}"]')
    el = driver.wait_for_xpath('//button[contains(.,"Next Page")]')
    assert not el.is_enabled()
    el = driver.wait_for_xpath('//button[contains(.,"Previous Page")]')
    assert not el.is_enabled()


def test_source_filtering_and_pagination(driver, user, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    for i in range(205):
        status, data = api(
            'POST',
            'sources',
            data={
                'id': f'{obj_id}_{i}',
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
        assert data['data']['id'] == f'{obj_id}_{i}'

    driver.get(f"/become_user/{user.id}")
    driver.get('/sources')

    driver.wait_for_xpath('//h2[contains(text(), "Sources")]')
    driver.wait_for_xpath('//td[text()="RRLyr"]')

    # Pagination
    next_button = '//button[contains(.,"Next Page")]'
    prev_button = '//button[contains(.,"Previous Page")]'

    driver.wait_for_xpath_to_be_unclickable(prev_button)
    driver.click_xpath(next_button)
    driver.wait_for_xpath_to_be_clickable(prev_button)

    driver.click_xpath(next_button)
    driver.wait_for_xpath_to_be_unclickable(next_button)

    driver.click_xpath(prev_button)
    driver.wait_for_xpath_to_be_clickable(next_button)

    driver.click_xpath(prev_button)
    driver.wait_for_xpath_to_be_unclickable(prev_button)

    # Jump to page
    jump_to_page_input = driver.wait_for_xpath("//input[@name='jumpToPageInputField']")
    jump_to_page_input.clear()
    jump_to_page_input.send_keys('3')
    jump_to_page_button = '//button[contains(.,"Jump to page:")]'
    driver.click_xpath(jump_to_page_button)
    driver.wait_for_xpath_to_be_clickable(prev_button)
    driver.wait_for_xpath_to_be_unclickable(next_button)

    jump_to_page_input.clear()
    jump_to_page_input.send_keys('1')
    driver.click_xpath(jump_to_page_button)
    driver.wait_for_xpath_to_be_clickable(next_button)
    driver.wait_for_xpath_to_be_unclickable(prev_button)

    # Source filtering
    driver.wait_for_xpath_to_be_clickable(next_button)
    obj_id = driver.wait_for_xpath("//input[@name='sourceID']")
    obj_id.clear()
    obj_id.send_keys('aaaa')
    submit = "//button[contains(.,'Submit')]"
    driver.click_xpath(submit)
    driver.wait_for_xpath_to_be_unclickable(next_button)


@pytest.mark.flaky(reruns=2)
def test_jump_to_page_invalid_values(driver):
    driver.get('/sources')
    jump_to_page_input = driver.wait_for_xpath("//input[@name='jumpToPageInputField']")
    jump_to_page_input.clear()
    jump_to_page_input.send_keys('abc')
    driver.click_xpath('//button[contains(.,"Jump to page:")]')
    driver.wait_for_xpath('//div[contains(.,"Invalid page number value")]')
