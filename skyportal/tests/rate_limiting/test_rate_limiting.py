import time
import socket
import requests
from baselayer.app.env import load_env
from skyportal.tests import api


_, cfg = load_env()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 53))
localhost_external_ip = s.getsockname()[0]
s.close()


def test_api_rate_limiting(view_only_token):
    # In case this test gets run after those defined below
    time.sleep(1)
    for n_successful_requests in range(100):
        r = requests.get(
            f'http://{localhost_external_ip}:{cfg["ports.app"]}/api/sysinfo',
            headers={'Authorization': f'token {view_only_token}'},
        )
        if r.status_code != 200:
            break
    assert 14 <= n_successful_requests <= 16
    r = requests.get(
        f'http://{localhost_external_ip}:{cfg["ports.app"]}/api/sysinfo',
        headers={'Authorization': f'token {view_only_token}'},
    )
    assert r.status_code == 429

    time.sleep(1)

    r = requests.get(
        f'http://{localhost_external_ip}:{cfg["ports.app"]}/api/sysinfo',
        headers={'Authorization': f'token {view_only_token}'},
    )
    assert r.status_code == 200


def test_rate_limited_requests_ok(view_only_token):
    for i in range(30):
        r = requests.get(
            f'http://{localhost_external_ip}:{cfg["ports.app"]}/api/sysinfo',
            headers={'Authorization': f'token {view_only_token}'},
        )
        assert r.status_code == 200
        time.sleep(0.2)


def test_localhost_unlimited(view_only_token):
    for i in range(30):
        status, _ = api('GET', 'sysinfo', token=view_only_token)
        assert status == 200
