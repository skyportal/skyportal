def safe_round(number, precision):
    return round(number, precision) if isinstance(number, int | float) else None
