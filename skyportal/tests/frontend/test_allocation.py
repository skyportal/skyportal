from selenium.webdriver.common.by import By
from skyportal.tests import api


def one_request_comment_process(
    driver, request_comment_xpath, actual_comment, comment_to_put
):
    # Add a comment to the first request by clicking the edit button
    driver.wait_for_xpath(request_comment_xpath + '//span').click()
    # Check that the comment in the pop-up is empty
    popup_textarea = driver.wait_for_xpath(
        '//div[@data-testid="updateCommentTextfield"]//textarea'
    )
    assert popup_textarea.text == actual_comment
    # Clear the text field
    popup_textarea.clear()
    # Enter the comment text and submit
    popup_textarea.send_keys(comment_to_put)
    driver.find_element(
        By.XPATH, '//button[@data-testid="updateCommentSubmitButton"]'
    ).click()
    assert driver.wait_for_xpath(request_comment_xpath).text == comment_to_put


def test_allocation_comment_display(
    driver, super_admin_user, public_group, public_source, super_admin_token, sedm
):
    # Create an allocation
    request_data = {
        'group_id': public_group.id,
        'instrument_id': sedm.id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
    }
    # Post the allocation
    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    # Check that the allocation was created
    assert status == 200
    assert data['status'] == 'success'
    allocation_id = data['data']['id']
    # Create one followup request with the allocation id
    request_data = {
        'allocation_id': allocation_id,
        'obj_id': public_source.id,
        'payload': {
            'priority': 5,
            'start_date': '3020-09-01',
            'end_date': '3022-09-01',
            'observation_type': 'IFU',
            'exposure_time': 300,
            'maximum_airmass': 2,
            'maximum_fwhm': 1.2,
        },
    }
    # Post the first followup request with no comment
    status, data = api(
        'POST', 'followup_request', data=request_data, token=super_admin_token
    )
    # Check that the followup request was created and get the request id
    assert status == 200
    assert data['status'] == 'success'
    # Create a second followup requests with the same allocation id
    request_data = {
        'allocation_id': allocation_id,
        'obj_id': public_source.id,
        'payload': {
            'priority': 5,
            'start_date': '4020-09-01',
            'end_date': '4022-09-01',
            'observation_type': 'IFU',
            'exposure_time': 200,
            'maximum_airmass': 1,
            'maximum_fwhm': 1.3,
        },
    }
    # Post the second followup request with no comment
    status, data = api(
        'POST', 'followup_request', data=request_data, token=super_admin_token
    )
    # Check that the second followup request was created and get the request id
    assert status == 200
    assert data['status'] == 'success'
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get(f'/allocation/{allocation_id}')

    # Get the comment div for each request
    request1_comment_xpath = '//tr[@data-testid="MUIDataTableBodyRow-0"]//span[@aria-label="Update comment"]/..'
    request2_comment_xpath = '//tr[@data-testid="MUIDataTableBodyRow-1"]//span[@aria-label="Update comment"]/..'
    request1_div_comment = driver.wait_for_xpath(request1_comment_xpath)
    request2_div_comment = driver.wait_for_xpath(request2_comment_xpath)
    # Check that each comment is empty
    assert request1_div_comment.text == ''
    assert request2_div_comment.text == ''

    one_request_comment_process(driver, request1_comment_xpath, '', 'comment number 1')

    one_request_comment_process(driver, request2_comment_xpath, '', 'comment number 2')

    one_request_comment_process(driver, request1_comment_xpath, 'comment number 1', '')

    driver.get(f'/allocation/{allocation_id}')
    request1_comment_xpath = '//tr[@data-testid="MUIDataTableBodyRow-0"]//span[@aria-label="Update comment"]/..'
    request2_comment_xpath = '//tr[@data-testid="MUIDataTableBodyRow-1"]//span[@aria-label="Update comment"]/..'
    assert driver.wait_for_xpath(request1_comment_xpath).text == ''
    assert driver.wait_for_xpath(request2_comment_xpath).text == 'comment number 2'
