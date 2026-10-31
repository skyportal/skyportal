import asyncio
import ctypes
import gc
import json
import os
import resource
import sys
import threading
import time
from collections import deque
from datetime import UTC, datetime

import psutil

from baselayer.app.access import permissions
from baselayer.log import make_log

from ...base import BaseHandler

log = make_log("memory")

PROBE_INTERVAL = 15 * 60  # seconds
HISTORY_LENGTH = 2 * 24 * 3600 // PROBE_INTERVAL
TRIM_POLL = 10  # seconds between checks for a trim request
TRIM_WAIT = 3 * TRIM_POLL
DIRECTORY = "run/memory"
TRIM_REQUEST = os.path.join(DIRECTORY, "trim")
FIELDS = (
    "rss_bytes",
    "uss_bytes",
    "pss_bytes",
    "peak_rss_bytes",
    "malloc_in_use_bytes",
    "malloc_free_bytes",
)

_recorder = None


class _MallInfo2(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_size_t)
        for name in (
            "arena",
            "ordblks",
            "smblks",
            "hblks",
            "hblkhd",
            "usmblks",
            "fsmblks",
            "uordblks",
            "fordblks",
            "keepcost",
        )
    ]


def _libc_function(name, restype, argtypes=()):
    """`name` from the C library, or None where it does not exist (outside glibc)."""
    try:
        function = getattr(ctypes.CDLL(None), name)
    except (OSError, AttributeError, TypeError):
        return None
    function.restype = restype
    function.argtypes = argtypes
    return function


_mallinfo2 = _libc_function("mallinfo2", _MallInfo2)
_malloc_trim = _libc_function("malloc_trim", ctypes.c_int, (ctypes.c_size_t,))


def _iso(timestamp):
    return datetime.fromtimestamp(timestamp, UTC).isoformat(timespec="seconds")


def _peak_rss(rss):
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != "darwin":
        peak *= 1024  # Linux reports KiB
    # The kernel updates the peak lazily, so it can trail the current RSS
    return max(peak, rss)


def probe(timestamp=None):
    """Memory of this process in bytes; None where the platform has no value."""
    memory = psutil.Process().memory_full_info()
    malloc = _mallinfo2() if _mallinfo2 else None
    return {
        "time": _iso(time.time() if timestamp is None else timestamp),
        "rss_bytes": memory.rss,
        "uss_bytes": getattr(memory, "uss", None),
        "pss_bytes": getattr(memory, "pss", None),
        "peak_rss_bytes": _peak_rss(memory.rss),
        "malloc_in_use_bytes": malloc.uordblks + malloc.hblkhd if malloc else None,
        "malloc_free_bytes": malloc.fordblks if malloc else None,
    }


def _trim(requested_at):
    before = probe()
    gc.collect()
    if _malloc_trim:
        _malloc_trim(0)
    result = {
        "requested_at": requested_at,
        "trimmed": _malloc_trim is not None,
        "before": before,
        "after": probe(),
    }
    log(json.dumps({"pid": os.getpid(), "trim": result}))
    return result


def _read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def _write(path, text):
    # Replace, so that readers never see a partly written file
    with open(f"{path}.tmp", "w") as f:
        f.write(text)
    os.replace(f"{path}.tmp", path)


def _remove_stale():
    cutoff = time.time() - HISTORY_LENGTH * PROBE_INTERVAL
    for name in os.listdir(DIRECTORY):
        path = os.path.join(DIRECTORY, name)
        if name.endswith(".json") and os.path.getmtime(path) < cutoff:
            os.remove(path)


def _next_probe(after):
    # On the clock, so that all processes share timestamps
    return (after // PROBE_INTERVAL + 1) * PROBE_INTERVAL


def _record(state, path, seen):
    history = deque(maxlen=HISTORY_LENGTH)
    trims = deque(maxlen=10)
    due = _next_probe(time.time())
    while True:
        time.sleep(max(min(due - time.time(), TRIM_POLL), 0))
        try:
            request = _read(TRIM_REQUEST)
            if request is not None and request != seen:
                seen = request
                trims.append(_trim(request))
            elif time.time() >= due:
                entry = probe(due)
                due = _next_probe(max(due, time.time()))
                history.append(entry)
                log(json.dumps({"pid": state["pid"], **entry}))
                _remove_stale()
            else:
                continue
            state["history"] = {
                key: [entry[key] for entry in history] for key in ("time", *FIELDS)
            }
            state["trims"] = list(trims)
            _write(path, json.dumps(state))
        except Exception as e:
            log(f"Could not record memory: {e}")


def _forked_from_zygote():
    try:
        parent = psutil.Process().parent()
        return parent is not None and any(
            os.path.basename(arg) == "zygote.py" for arg in parent.cmdline()
        )
    except psutil.Error:
        return False


def start_recording():
    """Record the memory history of this process; call once per web process."""
    # Not at import: the zygote imports this module and must fork from one thread
    global _recorder
    if _recorder is not None:
        return
    process = psutil.Process()
    state = {
        "pid": process.pid,
        "started_at": _iso(process.create_time()),
        "forked_from_zygote": _forked_from_zygote(),
        "history": {key: [] for key in ("time", *FIELDS)},
        "trims": [],
    }
    os.makedirs(DIRECTORY, exist_ok=True)
    # Read before the state file exists: POST waits for each process it can see
    seen = _read(TRIM_REQUEST)
    path = os.path.join(DIRECTORY, f"{process.pid}-{int(process.create_time())}.json")
    _write(path, json.dumps(state))
    _recorder = threading.Thread(
        target=_record, args=(state, path, seen), name="memory", daemon=True
    )
    _recorder.start()


def _running(pid, started_at):
    try:
        return _iso(psutil.Process(pid).create_time()) == started_at
    except psutil.Error:
        return False


def processes():
    """The recorded state of each web process on this host, oldest first."""
    try:
        names = os.listdir(DIRECTORY)
    except OSError:
        return []
    result = []
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            state = json.loads(_read(os.path.join(DIRECTORY, name)) or "")
        except ValueError:
            continue
        state["running"] = _running(state["pid"], state["started_at"])
        result.append(state)
    return sorted(result, key=lambda state: state["started_at"])


class MemoryHandler(BaseHandler):
    @permissions(["System admin"])
    def get(self):
        """
        ---
        summary: Show the memory history of the web processes
        description: |
          Each web process measures its own memory every 15 minutes, at :00,
          :15, :30 and :45 UTC, and keeps the measurements of the last 2 days.
          Each answer has the history of all web processes on the host that
          answers. If the instance runs on more than one host, each host has
          its own web processes, and the answer has only those of one host.

          `processes` has one entry for each web process, oldest first. A
          process that stopped keeps its entry for 2 days, with `running`
          false. A restarted process has a new entry, with a new `pid` and
          `started_at`. A new process has no measurements until the next
          quarter hour. Each measurement also goes to the app log as one line
          of JSON, with the same fields.

          All memory values are in bytes. A value is null if the platform does
          not supply it: `pss_bytes` needs Linux, and the `malloc_` values need
          glibc. All times are ISO 8601 in UTC. `history` has one list for each
          field, oldest first. Because all processes measure at the same times,
          the `time` lists of the processes agree.

          ## Fields

          - `rss_bytes`: resident set size. All physical memory that the
            process maps, including pages that it shares with other processes.
            Shared pages are shared libraries and, if `forked_from_zygote` is
            true, the code and data that the zygote loaded before it started
            this process. RSS counts each shared page in each process that uses
            it, so do not add RSS across processes.
          - `uss_bytes`: unique set size. Memory that only this process uses.
            The system gets this memory back when the process stops.
          - `pss_bytes`: proportional set size. USS plus an equal part of each
            shared page. The sum of PSS across processes is the physical memory
            that they use together.
          - `peak_rss_bytes`: highest RSS since the process started. A step in
            this value shows that a large request ran between two measurements.
          - `malloc_in_use_bytes`: memory that the C allocator (glibc malloc)
            gave out and that the program did not free. This includes Python
            objects larger than 512 bytes, NumPy arrays and most C libraries.
            It does not include small Python objects: Python's own allocator
            (pymalloc) gets their memory directly from the operating system.
            It also does not include Arrow buffers, which use jemalloc.
          - `malloc_free_bytes`: memory that the program freed, but that glibc
            keeps and did not give back to the operating system. RSS includes
            this memory, but new allocations can use it.

          In a process forked from the zygote, the `malloc_` values include the
          memory that the zygote allocated. Use their change over time, not
          their value.

          ## How to read the history

          Plot the fields against time for each web process. Then compare the
          plot with these patterns:

          - RSS rises fast after the start, then stays level. The process has
            reached its working size. This is normal.
          - RSS rises in steps at the same times as `peak_rss_bytes`. Large
            requests cause the steps. Memory that stays after such a request is
            usually in `malloc_free_bytes`. Find the requests and limit their
            size.
          - `malloc_free_bytes` rises and `malloc_in_use_bytes` stays level.
            The program frees memory, but glibc keeps it (fragmentation). This
            is not a leak. To confirm, send a POST (see below). To decrease it,
            set `MALLOC_ARENA_MAX=2`, use a different allocator, or restart
            the processes at intervals.
          - `malloc_in_use_bytes` rises with no limit. The program keeps more
            data over time: a cache with no size limit, or a leak. Find the
            code with a memory profiler, for example memray.
          - RSS rises, but the `malloc_` values do not. The growth is in small
            Python objects, Arrow buffers or other memory that does not come
            from glibc. Use memray with `--native`, or run one process with
            `PYTHONMALLOC=malloc` so that the `malloc_` values include small
            Python objects.
          - USS rises and RSS stays level (only if `forked_from_zygote` is
            true). The process writes to pages that it shares with the zygote,
            so the system copies these pages (copy-on-write). Changes to Python
            reference counts cause this. RSS does not change, but the system
            uses more memory in total. Changes to application code cannot stop
            this. A restart of the process shares the pages again.
          - The sum of PSS across processes rises. The instance needs more
            physical memory, for one of the reasons above.
          - The history of a process stops, `running` is false, and a new
            process starts at that time. The process stopped. If its memory was
            high just before, the system possibly stopped it because memory
            was low.

          `trims` lists the last trims of each process (see POST), so that the
          history shows how fast the memory rises again after a trim.
        tags:
          - system info
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        return self.success(
            data={"probe_interval_seconds": PROBE_INTERVAL, "processes": processes()}
        )

    @permissions(["System admin"])
    async def post(self):
        """
        ---
        summary: Give free memory of the web processes back to the operating system
        description: |
          Each web process that runs on the host that answers runs Python garbage
          collection, then tells glibc malloc to give its free memory back to
          the operating system (`malloc_trim`). Each process does this within
          10 seconds. The answer has, for each process, a measurement from
          before and after the trim, with the fields that GET describes.
          `trim` is null for a process that did not finish within 30 seconds.
          A process that starts after the request does not trim.
          `trimmed` is false where glibc is not available; then only the
          garbage collection runs. A process does not answer other requests
          while it trims, usually for less than a second.

          Use this to find out whether memory growth is a leak. If
          `rss_bytes` and `uss_bytes` drop by most of the growth, the memory
          was free, and glibc kept it. If they do not drop, the program still
          uses the memory. GET also lists each trim, so that the history shows
          how fast the memory rises again.
        tags:
          - system info
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        running = {
            (state["pid"], state["started_at"])
            for state in processes()
            if state["running"]
        }
        requested_at = datetime.now(UTC).isoformat()
        os.makedirs(DIRECTORY, exist_ok=True)
        _write(TRIM_REQUEST, requested_at)
        deadline = time.monotonic() + TRIM_WAIT
        while True:
            trims = {
                state["pid"]: next(
                    (t for t in state["trims"] if t["requested_at"] == requested_at),
                    None,
                )
                for state in processes()
                if (state["pid"], state["started_at"]) in running
            }
            if all(trims.values()) or time.monotonic() > deadline:
                break
            await asyncio.sleep(1)
        return self.success(
            data={
                "requested_at": requested_at,
                "processes": [
                    {"pid": pid, "trim": trim} for pid, trim in trims.items()
                ],
            }
        )
