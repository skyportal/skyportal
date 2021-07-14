import time
from skyportal.tests import api


def test_api_rate_limiting(view_only_token):
    n_successful_requests = 0
    status = 200
    while status == 200:
        status, _ = api('GET', 'sysinfo', token=view_only_token)
        n_successful_requests += 1
    assert n_successful_requests == 100
    status, data = api('GET', 'sysinfo', token=view_only_token)
    assert status == 503
    assert data["message"] == "API rate limit exceeded; please throttle your requests"

    time.sleep(5)

    status, _ = api('GET', 'sysinfo', token=view_only_token)
    assert status == 200
