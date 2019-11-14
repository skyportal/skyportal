import urllib.parse
import requests

from baselayer.app.env import load_env
env, cfg = load_env()


def api(method, endpoint, data=None, token=None):
    """Make a SkyPortal API call.

    Parameters
    ----------
    method : {'GET', 'POST', 'PUT', ...}
    endpoint : string
        Relative API endpoint.  E.g., `sources` means
        `http://localhost:port/api/sources`.
    data : dict
        Data to post.
    token : str
        A token, for when authentication is needed.  This is placed in the
        `Authorization` header.

    Returns
    -------
    code : str
        HTTP status code.
    json : dict
        Response JSON.
    """
    url = urllib.parse.urljoin(f'http://localhost:{cfg["ports.app"]}/api/',
                               endpoint)
    headers = {'Authorization': f'token {token}'} if token else None
    response = requests.request(method, url, json=data, headers=headers)
    return response.status_code, response.json()
