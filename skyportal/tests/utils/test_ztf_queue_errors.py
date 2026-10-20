"""ZTF queue calls raise the error ZTF sends back."""

import asyncio
from types import SimpleNamespace

import pytest

from skyportal.facility_apis import ztf


class _ErrorResponse:
    status = 500

    async def text(self):
        return "queue not found"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def get(self, *args, **kwargs):
        return _ErrorResponse()

    def delete(self, *args, **kwargs):
        return _ErrorResponse()


@pytest.fixture(autouse=True)
def ztf_errors(monkeypatch):
    monkeypatch.setattr(ztf, "aiohttp", SimpleNamespace(ClientSession=_Session))


ALLOCATION = SimpleNamespace(altdata={"access_token": "token"})


def test_remove_queue_raises_on_error():
    with pytest.raises(ValueError, match="Error deleting queue: queue not found"):
        asyncio.run(ztf.ZTFMMAAPI.remove_queue(ALLOCATION, "queue", "user"))


def test_queued_raises_on_error():
    with pytest.raises(ValueError, match="Error querying for queued observations"):
        asyncio.run(ztf.ZTFMMAAPI.queued(ALLOCATION))
