from skyportal.utils.parse import get_list_typed, get_page_and_n_per_page


def test_get_list_typed():
    assert get_list_typed("1,2,3", int) == [1, 2, 3]
    try:
        assert get_list_typed("1.0,2.0,3.0", int) == [1.0, 2.0, 3.0]
    except ValueError as e:
        assert str(e) == "Error parsing string to list of int."
    try:
        get_list_typed("1,a,3", int, "test error message")
    except ValueError as e:
        assert str(e) == "test error message"

    assert get_list_typed("1.0,2.0,3.0", float) == [1.0, 2.0, 3.0]
    assert get_list_typed("a,b,c", str) == ["a", "b", "c"]
    assert get_list_typed("1,a,3", str) == ["1", "a", "3"]

    assert get_list_typed("", int) == []
    assert get_list_typed("", str) == []
    assert get_list_typed("", float) == []

    assert get_list_typed(["1", "2", "3"], str) == ["1", "2", "3"]
    assert get_list_typed([1, 2, 3], str) == ["1", "2", "3"]
    assert get_list_typed([1, 2, 3], int) == [1, 2, 3]
    assert get_list_typed([1, 2, 3], float) == [1.0, 2.0, 3.0]


def test_get_page_and_n_per_page():
    assert get_page_and_n_per_page(1, 10) == (1, 10)
    assert get_page_and_n_per_page(1, 1000) == (1, 500)
    assert get_page_and_n_per_page(2, 1000, 200) == (2, 200)
    assert get_page_and_n_per_page(0, 0) == (0, 0)
    assert get_page_and_n_per_page("1", "10") == (1, 10)

    try:
        get_page_and_n_per_page("a", 10)
    except ValueError as e:
        assert str(e) == "Invalid page number value."

    try:
        get_page_and_n_per_page(1, "a")
    except ValueError as e:
        assert str(e) == "Invalid numPerPage value."

    try:
        get_page_and_n_per_page("1.0", 10)
    except ValueError as e:
        assert str(e) == "Invalid page number value."
