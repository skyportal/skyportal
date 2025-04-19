def get_int_list(text, error_msg="Error parsing string to int list"):
    """
    Convert a comma-separated string to a list of integers.
    If the input is already a list return it as a list of integers.
    """
    try:
        if isinstance(text, str):
            return [int(x.strip()) for x in text.split(",") if x.strip()]
        if isinstance(text, list):
            return [int(x) for x in text]
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
