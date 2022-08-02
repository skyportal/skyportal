# Taken from https://github.com/mwojnars/nifty/blob/master/util.py

import sys

# create logs at 2 MB
SIZE_WARNING_THRESHOLD = 2e6


def sizeof(obj):
    """Estimates total memory usage of (possibly nested) `obj` by recursively calling sys.getsizeof() for list/tuple/dict/set containers
    and adding up the results. Does NOT handle circular object references!
    """
    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        return size + sum(map(sizeof, obj.keys())) + sum(map(sizeof, obj.values()))
    if isinstance(obj, (list, tuple, set, frozenset)):
        return size + sum(map(sizeof, obj))
    return size
