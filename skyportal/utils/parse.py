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

    if page_number < 1:
        raise ValueError("Page number must be greater than 0.")
    if n_per_page < 1:
        raise ValueError("Number per page must be greater than 0.")

    return page_number, min(n_per_page, n_per_page_max)


def bool_to_int(value):
    """
    Convert a boolean value to an integer

    Parameters
    ----------
    value : bool
        The boolean value to convert.

    Returns
    -------
    int
        1 if the boolean value is True, 0 if it is False.

    Raises
    -------
    ValueError
        If the input value is not a boolean.
    """
    if not isinstance(value, bool):
        raise ValueError(f"Invalid boolean value: {value}")

    if value is True:
        return 1
    else:
        return 0


def str_to_bool(value, default=None):
    """
    Convert a string to a boolean value.

    Accepts various string representations:
        - "yes", "y", "true", "t", "1" => True
        - "no", "n", "false", "f", "0" => False

    If the value is None, empty, or invalid:
        - returns the default if provided
        - raises ValueError otherwise

    Parameters
    ----------
    value : str
        The string to convert to a boolean.
    default : bool, optional
        Value to return if the input is missing or invalid.

    Returns
    -------
    bool
        The converted boolean value.

    Raises
    -------
    ValueError
        If the value is invalid and no default is provided.
    """
    try:
        value_str = str(value).strip().lower()
        if value_str in ("yes", "y", "true", "t", "1"):
            return True
        if value_str in ("no", "n", "false", "f", "0"):
            return False
    except Exception:
        pass  # ignore any conversion error

    if default is not None:
        return default
    raise ValueError(f"Invalid string value for boolean conversion: {value}")


def is_null(value):
    """Check if a value is considered null.
    Parameters
    ----------
    value : any
        The value to check.
    Returns
    -------
    bool
        True if the value is null, False otherwise.
    """
    if isinstance(value, str):
        value = value.strip().lower()
    return value in [None, "", "none", "nan", "null"]


def safe_round(number, precision):
    return round(number, precision) if isinstance(number, int | float) else None
