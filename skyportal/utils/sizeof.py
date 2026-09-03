import sys

# create logs at 2 MB
SIZE_WARNING_THRESHOLD = 2e6


def sizeof(obj):
    """Estimate total memory usage of (possibly nested) ``obj`` by recursively
    calling ``sys.getsizeof()`` for list/tuple/dict/set/frozenset containers
    and adding up the results.

    Shared sub-objects are counted only once: traversal tracks ``id(obj)``
    so the same Group/User dict referenced from many places (a common shape
    in ``source_info``) is not double-counted. Cyclic references are also
    safe.
    """
    seen: set[int] = set()

    def _walk(node):
        node_id = id(node)
        if node_id in seen:
            return 0
        seen.add(node_id)
        size = sys.getsizeof(node)
        if isinstance(node, dict):
            size += sum(_walk(k) for k in node)
            size += sum(_walk(v) for v in node.values())
        elif isinstance(node, list | tuple | set | frozenset):
            size += sum(_walk(item) for item in node)
        return size

    return _walk(obj)
