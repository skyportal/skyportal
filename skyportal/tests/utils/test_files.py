import pytest

from skyportal.utils.files import check_path_string, filesize_to_human_readable


def test_check_path_string_valid():
    # word chars, underscore, dash, plus are allowed; empty is allowed
    check_path_string("valid_name-123+x")
    check_path_string("")
    # slashes only when explicitly permitted
    check_path_string("a/b/c", allow_slashes=True)


def test_check_path_string_invalid():
    for bad in ("with/slash", "has space", "dot.name", "weird*char"):
        with pytest.raises(ValueError, match="Illegal characters"):
            check_path_string(bad)


def test_filesize_to_human_readable():
    assert filesize_to_human_readable(512) == "512 B"
    assert filesize_to_human_readable(1024) == "1.0 KB"
    assert filesize_to_human_readable(1536) == "1.5 KB"
    assert filesize_to_human_readable(1024 * 1024) == "1.0 MB"
    assert filesize_to_human_readable(1024**3) == "1.0 GB"
    assert filesize_to_human_readable(5 * 1024**3) == "5.0 GB"
