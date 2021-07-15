import time
from skyportal.tests import api


def test_api_rate_limiting(view_only_token):
    n_successful_requests = 0
    status = 200
    while status == 200 and n_successful_requests < 100:
        status, _ = api('GET', 'sysinfo', token=view_only_token)
        if status == 200:
            n_successful_requests += 1
    assert 15 <= n_successful_requests <= 16
    status, data = api('GET', 'sysinfo', token=view_only_token)
    assert status != 200

    time.sleep(5)

    status, _ = api('GET', 'sysinfo', token=view_only_token)
    assert status == 200
