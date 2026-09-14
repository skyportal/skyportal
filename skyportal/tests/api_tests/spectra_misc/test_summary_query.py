from skyportal.tests import api


def test_bad_queries(view_only_token):
    # no query
    query_data = {}
    status, data = api("POST", "summary_query", data=query_data, token=view_only_token)
    assert status == 400
    assert data["message"].find("Missing one of the required") != -1

    # bad z range
    query_data = {
        "q": "Test query. This is my test query on the sources?",
        "z_min": 0.2,
        "z_max": 0.1,
    }
    status, data = api("POST", "summary_query", data=query_data, token=view_only_token)
    assert status == 400
    assert data["message"].find("z_min must be <= z_max") != -1

    # bad k
    query_data = {"q": "Test query. This is my test query on the sources?", "k": 101}
    status, data = api("POST", "summary_query", data=query_data, token=view_only_token)
    assert status == 400
    assert data["message"].find("k must be 1<=k<=100") != -1

    # send both a query and objID
    query_data = {
        "q": "Test query. This is my test query on the sources?",
        "objID": "ZTF20abm",
    }
    status, data = api("POST", "summary_query", data=query_data, token=view_only_token)
    assert status == 400
    assert data["message"].find("Cannot specify both") != -1


def test_cannot_search_from_a_source_you_cannot_see(
    view_only_token, public_source_group2
):
    """The neighbours of a summary describe it, so a source the requester cannot
    read is refused rather than answered."""
    status, data = api(
        "POST",
        "summary_query",
        data={"objID": public_source_group2.id},
        token=view_only_token,
    )
    assert status == 403, data
    assert "Cannot access object" in data["message"]


def test_searching_from_a_visible_source_is_not_refused(view_only_token, public_source):
    """The same request for a readable source gets past the access check; what it
    does next depends on the configured store."""
    status, data = api(
        "POST", "summary_query", data={"objID": public_source.id}, token=view_only_token
    )
    assert status != 403, data
