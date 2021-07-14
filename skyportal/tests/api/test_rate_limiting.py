import time
from baselayer.app.env import load_env
from skyportal.tests import api

_, cfg = load_env()


def test_api_rate_limiting(view_only_token):
    n_successful_requests = 0
    status = 200
    while status == 200:
        status, _ = api('GET', 'sysinfo', token=view_only_token)
        if status == 200:
            n_successful_requests += 1
    assert (
        100 * cfg["server"]["processes"] - 2
        <= n_successful_requests
        <= 100 * cfg["server"]["processes"] + 2
    )
    status, data = api('GET', 'sysinfo', token=view_only_token)
    assert status != 200
    assert "API rate limit exceeded; please throttle your requests" in data["message"]

    time.sleep(20)

    status, _ = api('GET', 'sysinfo', token=view_only_token)
    assert status == 200


def test_sys_admins_not_rate_limited(super_admin_token):
    for i in range(100 * cfg["server"]["processes"] + 5):
        status, _ = api('GET', 'sysinfo', token=super_admin_token)
        assert status == 200
