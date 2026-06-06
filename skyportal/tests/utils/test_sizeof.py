import sys

from skyportal.utils.sizeof import sizeof


def test_scalar_matches_getsizeof():
    assert sizeof(42) == sys.getsizeof(42)


def test_nested_container_larger_than_empty():
    assert sizeof({"a": [1, 2, 3]}) > sizeof({})


def test_shared_subobject_counted_once():
    shared = [1, 2, 3, 4, 5]
    once = sizeof({"a": shared, "b": shared})
    twice = sizeof({"a": [1, 2, 3, 4, 5], "b": [1, 2, 3, 4, 5]})
    assert once < twice


def test_handles_cyclic_references():
    d = {}
    d["self"] = d
    # must terminate (not infinite-recurse) and be positive
    assert sizeof(d) > 0
