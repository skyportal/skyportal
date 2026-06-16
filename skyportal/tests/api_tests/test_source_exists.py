from skyportal.tests import api


def test_source_exists_by_id_hit(view_only_token, public_source):
    """A known obj_id is reported as existing."""
    status, data = api(
        "GET", f"source_exists/{public_source.id}", token=view_only_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["source_exists"] is True
    assert public_source.id in data["data"]["message"]


def test_source_exists_by_id_miss(view_only_token):
    """An obj_id that doesn't exist (and no coords given) reports false."""
    status, data = api(
        "GET", "source_exists/ZTFnonexistent12345-async-test", token=view_only_token
    )
    assert status == 200
    assert data["data"]["source_exists"] is False


def test_source_exists_by_id_miss_with_coords_no_neighbours(view_only_token):
    """When the obj_id misses, the handler falls through to a cone search;
    a far-from-everything point should still come back negative."""
    status, data = api(
        "GET",
        "source_exists/ZTFnonexistent12345-async-test"
        "?ra=359.99&dec=-89.99&radius=0.001",
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["source_exists"] is False


def test_source_exists_requires_id_or_coords(view_only_token):
    """The endpoint refuses requests with neither an obj_id nor a cone."""
    status, data = api("GET", "source_exists", token=view_only_token)
    assert status == 400
    assert "obj_id" in data["message"] or "ra" in data["message"]


def test_source_exists_rejects_non_numeric_coords(view_only_token):
    """Non-float coord values fall back to None (via the type=float
    coercion in get_query_argument), so the request degrades to the
    'no spatial filter, no id' error path rather than 500ing."""
    status, data = api(
        "GET",
        "source_exists?ra=not-a-float&dec=not-a-float&radius=not-a-float",
        token=view_only_token,
    )
    assert status == 400
