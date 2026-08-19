import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import client


def test_db_stats(
    super_admin_token, public_source, public_group, public_candidate, user
):
    stats = client(super_admin_token).fetch_db_stats()
    assert isinstance(stats["Number of candidates"], int)
    assert isinstance(stats["Number of users"], int)


def test_db_stats_access_denied(
    view_only_token, public_source, public_group, public_candidate, user
):
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_db_stats()
    assert err.value.status_code == 401
