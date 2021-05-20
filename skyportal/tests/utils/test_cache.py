import shutil
import os
import time
from os.path import join as pjoin

import pytest

from skyportal.utils.offset import Cache


@pytest.fixture(scope="module")
def cache_parent_dir(tmpdir_factory):
    cache_parent = tmpdir_factory.mktemp("cache_test")
    yield cache_parent
    shutil.rmtree(str(cache_parent))


@pytest.fixture()
def cache(cache_parent_dir):
    cache_path = pjoin(cache_parent_dir, 'cache')
    cache = Cache(cache_path, max_items=3, max_age=3)
    yield cache
    shutil.rmtree(cache_path)


def test_cache_hit(cache):
    # Ensure cache directory was created
    assert os.path.isdir(cache._cache_dir)

    cache['some_key'] = b'abc'
    fn = cache['some_key']
    assert fn is not None


def test_cache_max_items(cache):
    cache['some_key'] = b'abc'
    assert len(cache) == 1

    cache['another_key'] = b'def'
    assert len(cache) == 2

    cache['yet_another_key'] = b'ghi'
    assert len(cache) == 3

    cache['the_last_straw'] = b'jkl'
    assert len(cache) == 3


def test_cache_cleanup(cache):
    for i in range(5):
        cache[str(i)] = b'x'
        time.sleep(0.5)

    for key in range(2, 5):
        assert cache[str(key)] is not None


def test_cache_cleanup_by_age(cache):
    cache['first'] = b'one'
    f = cache['first']
    assert f is not None

    # Let object time out of cache
    time.sleep(3)

    f = cache['first']
    assert f is None


def test_cache_reference_refresh(cache):
    """Last referred item should be last to be removed from cache."""
    for i in range(3):
        cache[str(i)] = b'x'

    time.sleep(1)  # ensure that timestamp is different
    cache['0']

    cache['3'] = b'x'
    cache['4'] = b'x'

    assert cache['0'] is not None


def test_cache_nested_root(cache_parent_dir):
    Cache(cache_parent_dir / 'some/deeper/path', 1)


def test_cache_no_max_limit(cache_parent_dir):
    cache = Cache(
        pjoin(cache_parent_dir, 'cache_nm_limit'), max_items=None, max_age=None
    )
    for i in range(100):
        cache[str(i)] = b'x'

    assert len(cache) == 100
