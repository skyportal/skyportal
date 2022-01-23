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
