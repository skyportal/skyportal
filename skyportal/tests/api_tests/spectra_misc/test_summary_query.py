from baselayer.app.models import DBSession
from skyportal.tests import api
from skyportal.utils.embedding_store import upsert_embedding


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


MODEL = "test-embedding"


def _store(obj_id, vector):
    """Put one vector in the store the way the webhook would."""
    DBSession().execute(upsert_embedding(obj_id, vector, MODEL))
    DBSession().commit()


def test_similar_sources_come_back_nearest_first(
    view_only_token, public_source, public_source_no_data
):
    """The stored vectors are searched for real: no embedding service is needed
    to ask which summaries resemble one already indexed."""
    _store(public_source.id, [1.0, 0.0, 0.0])
    _store(public_source_no_data.id, [0.9, 0.1, 0.0])

    status, data = api(
        "POST",
        "summary_query",
        data={"objID": public_source.id, "k": 5},
        token=view_only_token,
    )
    assert status == 200, data
    results = data["data"]["query_results"]
    ids = [r["id"] for r in results]
    # the anchor describes itself perfectly and would otherwise lead every result
    assert public_source.id not in ids
    assert public_source_no_data.id in ids
    assert results[0]["score"] > 0.9


def test_a_source_in_another_group_is_not_a_result(
    view_only_token, public_source, public_source_no_data, public_source_group2
):
    """Group membership decides what the search may return, not just what it may
    be asked about."""
    _store(public_source.id, [1.0, 0.0, 0.0])
    _store(public_source_no_data.id, [0.9, 0.1, 0.0])
    _store(public_source_group2.id, [1.0, 0.0, 0.0])

    status, data = api(
        "POST",
        "summary_query",
        data={"objID": public_source.id, "k": 50},
        token=view_only_token,
    )
    assert status == 200, data
    ids = [r["id"] for r in data["data"]["query_results"]]
    assert public_source_group2.id not in ids
    assert public_source_no_data.id in ids


def test_k_bounds_the_results(view_only_token, public_source, public_source_no_data):
    _store(public_source.id, [1.0, 0.0, 0.0])
    _store(public_source_no_data.id, [0.9, 0.1, 0.0])

    status, data = api(
        "POST",
        "summary_query",
        data={"objID": public_source.id, "k": 1},
        token=view_only_token,
    )
    assert status == 200, data
    assert len(data["data"]["query_results"]) <= 1


def test_a_source_with_no_stored_vector_returns_nothing(
    view_only_token, public_source, public_source_no_data
):
    """An un-indexed source is simply absent from the search, not an error."""
    _store(public_source_no_data.id, [0.9, 0.1, 0.0])

    status, data = api(
        "POST",
        "summary_query",
        data={"objID": public_source.id},
        token=view_only_token,
    )
    assert status == 200, data
    assert data["data"]["query_results"] == []
