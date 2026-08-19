import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import api, client


def test_source_exists_by_id_hit(view_only_token, public_source):
    """A known obj_id is reported as existing."""
    result = client(view_only_token).fetch_source_exists(public_source.id)
    assert result.source_exists is True
    assert public_source.id in result.message


def test_source_exists_by_id_miss(view_only_token):
    """An obj_id that doesn't exist (and no coords given) reports false."""
    result = client(view_only_token).fetch_source_exists(
        "ZTFnonexistent12345-async-test"
    )
    assert result.source_exists is False


def test_source_exists_by_id_miss_with_coords_no_neighbours(view_only_token):
    """When the obj_id misses, the handler falls through to a cone search;
    a far-from-everything point should still come back negative."""
    result = client(view_only_token).fetch_source_exists(
        "ZTFnonexistent12345-async-test", ra=359.99, dec=-89.99, radius=0.001
    )
    assert result.source_exists is False


def test_source_exists_requires_id_or_coords(view_only_token):
    """The endpoint refuses requests with neither an obj_id nor a cone."""
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_source_exists()
    assert err.value.status_code == 400
    assert "obj_id" in str(err.value) or "ra" in str(err.value)


def test_source_exists_rejects_non_numeric_coords(view_only_token):
    """Non-float coord values fall back to None (via the type=float
    coercion in get_query_argument), so the request degrades to the
    'no spatial filter, no id' error path rather than 500ing."""
    # raw api: intentionally malformed payload the typed client can't produce
    # (non-numeric ra/dec/radius query values)
    status, data = api(
        "GET",
        "source_exists?ra=not-a-float&dec=not-a-float&radius=not-a-float",
        token=view_only_token,
    )
    assert status == 400
