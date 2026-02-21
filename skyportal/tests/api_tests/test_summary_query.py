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
