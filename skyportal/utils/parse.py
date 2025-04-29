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
    Convert a string to a boolean value

    Accepts various string representations of boolean values.
    For example:
        - "yes", "y", "true", "t", "1" -> True
        - "no", "n", "false", "f", "0" -> False
    If the string does not match any of these, it raises a ValueError.
    If default is provided and the string does not match any of the accepted values,
    it returns the default value instead of raising an error.

    Parameters
    ----------
    value : str
        The string to convert to a boolean.
    default : bool, optional
        The default value to return if the string does not match any of the accepted values.
        If not provided and the string does not match any of the accepted values, a ValueError is raised.

    Returns
    -------
    bool
        The converted boolean value.

    Raises
    -------
    ValueError
        If the string does not match any of the accepted values and no default is provided.
    """
    try:
        value = str(value).strip().lower()
    except Exception:
        raise ValueError(f"Invalid string value for boolean conversion: {value}")

    if value in ("yes", "y", "true", "t", "1"):
        return True
    elif value in ("no", "n", "false", "f", "0"):
        return False
    elif default is not None:
        return default
    else:
        raise ValueError(f"Invalid string value for boolean conversion: {value}")
