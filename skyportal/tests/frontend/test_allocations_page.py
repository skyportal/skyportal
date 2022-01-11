from skyportal.tests import api


def test_super_user_post_allocation(
    sedm, public_group, super_admin_token, super_admin_user, driver
):

    request_data = {
        'group_id': public_group.id,
        'instrument_id': sedm.id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
    }

    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'allocation/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/allocations")

    driver.wait_for_xpath('//div[contains(text(), "SEDM")]')
