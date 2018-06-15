import pytest
import uuid
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from skyportal.model_util import create_token


def test_token_user_post_photometry_data(driver, public_group, public_source):
    auth_token = create_token(public_group.id, ['Upload data'])
    response = driver.request(
        'POST', f'{driver.server_url}/api/photometry',
        json={'token': auth_token,
              'sourceID': str(public_source.id),
              'obsTime': str(datetime.datetime.now()),
              'instrumentID': 1,
              'mag': 12.24,
              'e_mag': 0.031,
              'lim_mag': 14.1,
              'filter': 'V'
        }).json()
    print(response)
    assert response['status'] == 'success'
