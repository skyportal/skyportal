"""The container gives itself a secret key rather than running on the shipped one.

The app refuses to start on config.yaml.defaults' key, and the image bakes
docker.yaml in as config.yaml, so without this every container from the image
would refuse to start.
"""

import pathlib

import pytest
import yaml

from skyportal.utils.secret_key import ensure_secret_key


@pytest.fixture()
def run(tmp_path, monkeypatch):
    """Run the generator against a config in a scratch directory."""

    def _run(config_text):
        monkeypatch.chdir(tmp_path)
        pathlib.Path("config.yaml").write_text(config_text)
        ensure_secret_key()
        config = yaml.safe_load(pathlib.Path("config.yaml").read_text()) or {}
        return (config.get("app") or {}).get("secret_key")

    return _run


def test_the_shipped_key_is_replaced(run):
    key = run("app:\n  secret_key: abc01234\n  sedm_endpoint:\n")
    assert key not in (None, "abc01234")
    assert len(key) > 20


def test_a_missing_key_is_added_to_the_app_block(run):
    key = run("app:\n  sedm_endpoint:\n")
    assert key and len(key) > 20


def test_a_config_with_no_app_block_gets_one(run):
    # Writing the key to the volume and not to the config would leave the app
    # on the key it refuses to start with, silently.
    key = run("database:\n  user: skyportal\n")
    assert key and len(key) > 20


def test_a_key_someone_chose_is_left_alone(run):
    assert run("app:\n  secret_key: chosen-by-a-human\n") == "chosen-by-a-human"


def test_the_key_survives_a_restart(run, tmp_path):
    first = run("app:\n  secret_key: abc01234\n")
    # Same volume, config reset to the shipped default: the stored key returns
    # rather than every restart invalidating outstanding sessions.
    second = run("app:\n  secret_key: abc01234\n")
    assert first == second


def test_other_settings_are_not_disturbed(run, tmp_path):
    run("app:\n  secret_key: abc01234\n  sedm_endpoint:\n  ps1_cutout_url:\n")
    config = yaml.safe_load((tmp_path / "config.yaml").read_text())
    assert set(config["app"]) == {"secret_key", "sedm_endpoint", "ps1_cutout_url"}


def test_replicas_on_one_volume_agree(tmp_path, monkeypatch):
    # Two containers sharing the persistentdata volume must end up with the
    # same key: nginx will route a websocket to either, and auth is only valid
    # on the process that issued the session.
    monkeypatch.chdir(tmp_path)
    keys = set()
    for _ in range(2):
        pathlib.Path("config.yaml").write_text("app:\n  secret_key: abc01234\n")
        ensure_secret_key()
        config = yaml.safe_load(pathlib.Path("config.yaml").read_text())
        keys.add(config["app"]["secret_key"])
    assert len(keys) == 1


def test_a_key_file_left_empty_by_a_crash_is_replaced(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = tmp_path / "persistentdata" / "secret_key"
    store.parent.mkdir()
    store.write_text("")
    pathlib.Path("config.yaml").write_text("app:\n  secret_key: abc01234\n")
    ensure_secret_key()
    config = yaml.safe_load(pathlib.Path("config.yaml").read_text())
    assert config["app"]["secret_key"] not in (None, "", "abc01234")
    assert store.read_text().strip() == config["app"]["secret_key"]
