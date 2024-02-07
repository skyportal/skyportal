import requests

from baselayer.app.env import load_env

_, cfg = load_env()

server_url = f'http://localhost:{cfg["ports.app"]}'


def test_brotli():
    # Test that the server is using Brotli compression
    # when requested by the client
    r = requests.get(server_url, headers={"Accept-Encoding": "br"})
    print(r.status_code)
    print(r.headers)
    assert r.status_code == 200
    assert r.headers.get("Content-Encoding") == "br"
