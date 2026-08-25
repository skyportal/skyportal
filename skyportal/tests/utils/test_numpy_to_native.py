"""Unit tests for ``skyportal.handlers.api.photometry.numpy_to_native``.

The helper turns numpy scalars/arrays (which appear all over the photometry
ingest path because the params dicts come from ``DataFrame.to_dict('records')``)
into Python native types so they can be JSON-serialized for JSONB columns
without the ``Object of type float64 is not JSON serializable`` failure mode.
"""

import json

import numpy as np

from skyportal.handlers.api.photometry import numpy_to_native


def test_numpy_to_native_scalars():
    """All numpy scalar types convert to their Python equivalents."""
    assert numpy_to_native(np.float64(1.5)) == 1.5
    assert isinstance(numpy_to_native(np.float64(1.5)), float)

    assert numpy_to_native(np.int64(7)) == 7
    assert isinstance(numpy_to_native(np.int64(7)), int)

    assert numpy_to_native(np.bool_(True)) is True
    assert isinstance(numpy_to_native(np.bool_(True)), bool)


def test_numpy_to_native_ndarray():
    """1-D and 2-D ndarrays come back as nested Python lists with native
    leaf types."""
    arr = np.array([1.0, 2.0, 3.0])
    out = numpy_to_native(arr)
    assert out == [1.0, 2.0, 3.0]
    assert all(isinstance(x, float) for x in out)

    arr2 = np.array([[1, 2], [3, 4]])
    out2 = numpy_to_native(arr2)
    assert out2 == [[1, 2], [3, 4]]
    assert all(isinstance(row, list) for row in out2)
    assert all(isinstance(x, int) for row in out2 for x in row)


def test_numpy_to_native_nested_dict_and_list():
    """Recursion walks into dicts and lists, converting embedded numpy
    values at any depth. The original packet shape is preserved."""
    packet = {
        "obj_id": "abc",
        "mjd": np.float64(60000.5),
        "fluxes": [np.float32(1.0), np.float64(2.0)],
        "altdata": {
            "exptime": np.int64(30),
            "ok": np.bool_(False),
            "history": [{"mag": np.float64(20.5)}],
        },
    }
    out = numpy_to_native(packet)
    assert out["obj_id"] == "abc"
    assert out["mjd"] == 60000.5
    assert isinstance(out["mjd"], float)
    assert out["fluxes"] == [1.0, 2.0]
    assert all(isinstance(x, float) for x in out["fluxes"])
    assert out["altdata"]["exptime"] == 30
    assert isinstance(out["altdata"]["exptime"], int)
    assert out["altdata"]["ok"] is False
    assert out["altdata"]["history"][0]["mag"] == 20.5
    assert isinstance(out["altdata"]["history"][0]["mag"], float)


def test_numpy_to_native_pass_through_native():
    """Already-native values are returned unchanged (object identity not
    required, just equality + type)."""
    assert numpy_to_native(None) is None
    assert numpy_to_native(5) == 5
    assert isinstance(numpy_to_native(5), int)
    assert numpy_to_native("hello") == "hello"
    assert numpy_to_native(3.14) == 3.14
    assert numpy_to_native(True) is True


def test_numpy_to_native_output_is_json_serializable():
    """End-to-end guarantee: anything ``numpy_to_native`` returns can be
    handed to ``json.dumps``. This is the property that lets us drop the
    ``json.loads(json.dumps(..., NumpyEncoder))`` round-trip at the
    pg_insert callsite."""
    packet = {
        "mjd": np.float64(59000.123),
        "fluxes": np.array([1.0, 2.0, 3.0]),
        "meta": {"n": np.int64(42), "ok": np.bool_(True)},
    }
    encoded = json.dumps(numpy_to_native(packet))
    decoded = json.loads(encoded)
    assert decoded == {
        "mjd": 59000.123,
        "fluxes": [1.0, 2.0, 3.0],
        "meta": {"n": 42, "ok": True},
    }
