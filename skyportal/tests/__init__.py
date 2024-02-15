import os
import urllib.parse
import requests

from .patch_requests import patch_requests
from baselayer.app.env import load_env


IS_CI_BUILD = "TRAVIS" in os.environ or "GITHUB_ACTIONS" in os.environ

patch_requests()

session = requests.Session()
session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)


def api(
    method, endpoint, data=None, params=None, host=None, token=None, raw_response=False
):
    """Make a SkyPortal API call.

    Parameters
    ----------
    method : {'GET', 'POST', 'PUT', ...}
        HTTP method.
    endpoint : string
        Relative API endpoint.  E.g., `sources` means
        `http://localhost:port/api/sources`.
    data : dict
        Data to post
    params : dict
        URL parameters, in GET
    host : str
        Defaults to http://localhost on the port specified in the
        SkyPortal configuration file.
    token : str
        A token, for when authentication is needed.  This is placed in the
        `Authorization` header.
    raw_response : bool
        Return the response object, instead of the status code and parsed json.

    Returns
    -------
    code : str
        HTTP status code, if `raw_response` is False.
    json : dict
        Response JSON, if `raw_response` is False.
    """
    if host is None:
        env, cfg = load_env()
        host = f'http://localhost:{cfg["ports.app"]}'
    url = urllib.parse.urljoin(host, f'/api/{endpoint}')
    headers = {'Authorization': f'token {token}'} if token else None
    response = session.request(method, url, json=data, params=params, headers=headers)

    if raw_response:
        return response
    else:
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            data = None
        return response.status_code, data


def assert_api(status, data):
    """
    Check that the API call succeeded.
    If it fails, prints out the error message,
    before raising an exception.

    Parameters
    ----------
    status: int
        The status code of the response.
    data: dict
        The response data.

    """
    if status != 200 or data['status'] != 'success':
        if data:
            raise Exception(f'Expected success, got {status}: {data["message"]}')
        else:
            raise Exception(f'Expected success, got {status}')


def assert_api_fail(status, data, expected_status=None, expected_error_partial=None):
    """
    Check that the API call failed.
    If it succeeds, raise an exception.
    Optionally, check that the status code and error message
    are as expected.

    Parameters
    ----------
    status: int
        The status code of the response.
    data: dict
        The response data.
    expected_status: int (optional)
        The expected status code.
    expected_error_partial: str (optional)
        The expected error message.
        If this message is not found in the error message,
        will raise an exception.

    """
    if status == 200:
        raise Exception(f'Expected failure, got status==200')
    if expected_error_partial is not None:
        if not data or expected_error_partial not in data['message']:
            raise Exception(
                f'Expected error message to contain {expected_error_partial}, got {data["message"]}'
            )
    if expected_status is not None:
        if status != expected_status:
            raise Exception(f'Expected status {expected_status}, got {status}')
