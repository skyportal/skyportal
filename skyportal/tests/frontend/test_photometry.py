import pytest
import uuid
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
import requests

from skyportal.model_util import create_token


def test_token_user_post_photometry_data(driver, public_group, public_source):
    auth_token = create_token(public_group.id, ['Upload data'])
    response = requests.post(f'{driver.server_url}/api/photometry',
                             json={'sourceID': str(public_source.id),
                                   'obsTime': str(datetime.datetime.now()),
                                   'timeFormat': 'iso',
                                   'timeScale': 'utc',
                                   'instrumentID': 1,
                                   'mag': 12.24,
                                   'e_mag': 0.031,
                                   'lim_mag': 14.1,
                                   'filter': 'V'
                             },
                             headers={'Authorization': f'token {auth_token}'}
    ).json()
    assert response['status'] == 'success'


def test_token_user_post_photometry_data_series(driver, public_group, public_source):
    auth_token = create_token(public_group.id, ['Upload data'])
    response = requests.post(
        f'{driver.server_url}/api/photometry',
        json={'sourceID': str(public_source.id),
              'obsTime': [str(datetime.datetime.now()),
                          str(datetime.datetime.now() + datetime.timedelta(days=1)),
                          str(datetime.datetime.now() + datetime.timedelta(days=2))],
              'timeFormat': 'iso',
              'timeScale': 'utc',
              'instrumentID': 1,
              'mag': [12.24, 12.52, 12.70],
              'e_mag': [0.031, 0.029, 0.030],
              'lim_mag': 14.1,
              'filter': 'V'},
        headers={'Authorization': f'token {auth_token}'}
    ).json()
    assert response['status'] == 'success'
