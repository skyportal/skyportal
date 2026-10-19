import gc
import os
import sys
import tracemalloc
from collections import defaultdict

from baselayer.app.access import permissions

from ...base import BaseHandler

TRACE_FRAMES = 25
MiB = 1024 * 1024


def _rss_mib():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return round(int(line.split()[1]) / 1024, 1)
    return None


def _object_counts(top):
    counts = defaultdict(lambda: [0, 0])
    for obj in gc.get_objects():
        entry = counts[type(obj).__qualname__]
        entry[0] += 1
        entry[1] += sys.getsizeof(obj, 0)
    ranked = sorted(counts.items(), key=lambda item: item[1][1], reverse=True)
    return [
        {"type": name, "count": count, "size_mib": round(size / MiB, 2)}
        for name, (count, size) in ranked[:top]
    ]


def _frame(frame):
    return f"{frame.filename}:{frame.lineno}"


def _allocations(top):
    snapshot = tracemalloc.take_snapshot().filter_traces(
        [tracemalloc.Filter(False, tracemalloc.__file__)]
    )
    allocations = []
    for stat in snapshot.statistics("traceback")[:top]:
        app_frames = [
            frame
            for frame in stat.traceback
            if "/skyportal/" in frame.filename and "/.venv/" not in frame.filename
        ]
        allocations.append(
            {
                "size_mib": round(stat.size / MiB, 2),
                "count": stat.count,
                "where": _frame(stat.traceback[-1]),
                "app_frame": _frame(app_frames[-1]) if app_frames else None,
            }
        )
    return allocations


class MemoryHandler(BaseHandler):
    @permissions(["System admin"])
    async def get(self):
        """
        ---
        summary: Inspect the memory of a web process
        description: |
          Answered by whichever web process receives the request. Returns its
          pid, its resident memory, the live Python objects that take the most
          memory, and, while allocation tracing runs in that process, the code
          that allocated the most memory still in use.
        tags:
          - system info
        parameters:
          - in: query
            name: trace
            required: false
            schema:
              type: string
              enum: [start, stop]
            description: Start or stop allocation tracing in the process that answers.
          - in: query
            name: top
            required: false
            schema:
              type: integer
              default: 30
            description: How many object types and allocation sites to return.
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        trace = self.get_query_argument("trace", None)
        try:
            top = int(self.get_query_argument("top", "30"))
        except ValueError:
            return self.error("top must be an integer")
        if trace == "start" and not tracemalloc.is_tracing():
            tracemalloc.start(TRACE_FRAMES)
        elif trace == "stop" and tracemalloc.is_tracing():
            tracemalloc.stop()

        data = {
            "pid": os.getpid(),
            "rss_mib": _rss_mib(),
            "objects": _object_counts(top),
            "tracing": tracemalloc.is_tracing(),
        }
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            data["traced_mib"] = round(current / MiB, 1)
            data["traced_peak_mib"] = round(peak / MiB, 1)
            data["allocations"] = _allocations(top)
        return self.success(data=data)
