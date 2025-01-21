import socket
import time

import requests

from baselayer.app.env import load_env
from skyportal.tests import api

_, cfg = load_env()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 53))
localhost_external_ip = s.getsockname()[0]
s.close()


def test_api_rate_limiting(view_only_token):
    # In case this test gets run after those defined below, wait until no previous
    # requests count against our rate limit
    time.sleep(1)
    for n_successful_requests in range(100):
        r = requests.get(
            f"http://{localhost_external_ip}:{cfg['ports.app']}/api/sysinfo",
            headers={"Authorization": f"token {view_only_token}"},
        )
        if r.status_code != 200:
            break
    # Based on baselayer's default nginx settings of max 10r/s + bursts of 10 (no delay)
    # See https://www.nginx.com/blog/rate-limiting-nginx/#bursts
    assert 11 <= n_successful_requests <= 20
    r = requests.get(
        f"http://{localhost_external_ip}:{cfg['ports.app']}/api/sysinfo",
        headers={"Authorization": f"token {view_only_token}"},
    )
    assert r.status_code == 429

    # Wait until no previous requests count against rate limit
    time.sleep(1)

    # Ensure request is now successful
    r = requests.get(
        f"http://{localhost_external_ip}:{cfg['ports.app']}/api/sysinfo",
        headers={"Authorization": f"token {view_only_token}"},
    )
    assert r.status_code == 200


def test_rate_limited_requests_ok(view_only_token):
    # This is above the 15/s (regular + burst) threshold, but throttled down:
    for i in range(30):
        r = requests.get(
            f"http://{localhost_external_ip}:{cfg['ports.app']}/api/sysinfo",
            headers={"Authorization": f"token {view_only_token}"},
        )
        assert r.status_code == 200
        # Bring down to ~ default rate limit of 5r/s -- should never hit limit
        time.sleep(0.2)


def test_localhost_unlimited(view_only_token):
    for i in range(30):
        # Here we're using regular localhost, not the "external"-appearing IP,
        # which is exempted by default in baselayer's nginx config
        status, _ = api("GET", "sysinfo", token=view_only_token)
        assert status == 200
