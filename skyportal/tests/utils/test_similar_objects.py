import requests

from skyportal.broker_apis import boom
from skyportal.broker_apis.boom import BOOMBROKER
from skyportal.utils.similarity import no_neighbors_reason


def test_boom_similar_objects_tells_missing_embedding_from_no_results(monkeypatch):
    def not_found(*args, **kwargs):
        response = requests.Response()
        response.status_code = 404
        raise requests.HTTPError(response=response)

    monkeypatch.setattr(boom, "_request", not_found)
    assert (
        BOOMBROKER.similar_objects(None, "ZTF19abaeyqw", None, permissions=None) is None
    )
    # not searched at all: no embedding is claimed missing
    assert BOOMBROKER.similar_objects(None, "2019kcy", None, permissions=None) == []
    assert BOOMBROKER.similar_objects(None, "ZTF19abaeyqw", None, permissions={}) == []

    monkeypatch.setattr(boom, "_request", lambda *a, **k: {"neighbors": []})
    assert (
        BOOMBROKER.similar_objects(None, "ZTF19abaeyqw", None, permissions=None) == []
    )


def test_no_neighbors_reason():
    hit = [{"object_id": "ZTF20abjwjrx", "score": 0.9}]
    assert no_neighbors_reason("ZTF19abaeyqw", None, ("ZTF",)) == "no_embedding"
    assert no_neighbors_reason("2019kcy", [], ("ZTF",)) == "survey"
    assert no_neighbors_reason("ZTF19abaeyqw", [], ("ZTF",)) is None
    assert no_neighbors_reason("ZTF19abaeyqw", hit, ("ZTF",)) is None
    # a broker that lists no surveys never blames the survey
    assert no_neighbors_reason("2019kcy", [], ()) is None
