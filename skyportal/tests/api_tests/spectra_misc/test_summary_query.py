import pytest
from skyportal_py import SkyPortalError
from skyportal_py.summary_query import SummaryQueryPost

from skyportal.tests import client


def test_bad_queries(view_only_token):
    sp = client(view_only_token)
    # no query
    with pytest.raises(SkyPortalError, match="Missing one of the required") as err:
        sp.post_summary_query(SummaryQueryPost())
    assert err.value.status_code == 400

    # bad z range
    with pytest.raises(SkyPortalError, match="z_min must be <= z_max") as err:
        sp.post_summary_query(
            SummaryQueryPost(
                q="Test query. This is my test query on the sources?",
                z_min=0.2,
                z_max=0.1,
            )
        )
    assert err.value.status_code == 400

    # bad k
    with pytest.raises(SkyPortalError, match="k must be 1<=k<=100") as err:
        sp.post_summary_query(
            SummaryQueryPost(
                q="Test query. This is my test query on the sources?", k=101
            )
        )
    assert err.value.status_code == 400

    # send both a query and objID
    with pytest.raises(SkyPortalError, match="Cannot specify both") as err:
        sp.post_summary_query(
            SummaryQueryPost(
                q="Test query. This is my test query on the sources?",
                obj_id="ZTF20abm",
            )
        )
    assert err.value.status_code == 400
