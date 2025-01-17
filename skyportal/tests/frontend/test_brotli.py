import requests

from baselayer.app.env import load_env

_, cfg = load_env()

server_url = f"http://localhost:{cfg['ports.app']}"


def test_brotli():
    r = requests.get(server_url, headers={"Accept-Encoding": "br"})
    assert r.status_code == 200
    assert r.headers.get("Content-Encoding") == "br"
