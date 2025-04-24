def get_list_typed(text, dtype, error_msg=None):
    """
    Convert a comma-separated string to a list of the specified type.
    If the input is already a list return it as a list of the specified type.
    """
    error_msg = error_msg or f"Error parsing string to list of {dtype.__name__}."
    try:
        if isinstance(text, str):
            return [dtype(x.strip()) for x in text.split(",") if x.strip()]
        if isinstance(text, list):
            return [dtype(str(x).strip()) for x in text]
        else:
            raise ValueError(error_msg)
    except Exception:
        raise ValueError(error_msg)


def get_page_and_n_per_page(page_number, n_per_page, n_per_page_max=500):
    try:
        page_number = int(page_number)
    except ValueError:
        raise ValueError("Invalid page number value.")
    try:
        n_per_page = int(n_per_page)
    except ValueError:
        raise ValueError("Invalid numPerPage value.")
    return page_number, min(n_per_page, n_per_page_max)


def bool_to_int(value):
    """
    Convert a boolean value to an integer
    """
    if isinstance(value, bool):
        if value is True:
            return 1
        else:
            return 0
    raise ValueError(f"Invalid boolean value: {value}")
