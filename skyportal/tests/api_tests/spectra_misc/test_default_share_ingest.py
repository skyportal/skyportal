import asyncio

import pytest

from baselayer.app import models as baselayer_models
from skyportal.handlers.api.photometry import get_group_ids
from skyportal.models import User
from skyportal.utils import data_access


def resolve_group_ids(user_id, apply_default_share):
    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            user = await session.get(User, user_id)
            return await get_group_ids(
                {}, user, session, apply_default_share=apply_default_share
            )

    return asyncio.run(_run())


@pytest.fixture()
def default_share_on(monkeypatch, public_group):
    """Turn on the config default-share, targeting the public_group fixture."""
    monkeypatch.setattr(
        data_access,
        "cfg",
        {
            "misc.share_data_with_public_group_by_default": True,
            "misc.public_group_name": public_group.name,
        },
    )
    return public_group


def test_default_share_applies_to_normal_upload(default_share_on, user):
    """With default-share on and no groups given, an upload picks up the sitewide
    public group (apply_default_share defaults to True)."""
    group_ids = resolve_group_ids(user.id, apply_default_share=True)
    assert default_share_on.id in group_ids


def test_default_share_skipped_for_broker_ingestion(default_share_on, user):
    """Broker ingestion passes apply_default_share=False, so ingested data is not
    auto-shared with the sitewide public group even when the flag is on. It stays
    scoped to the uploader's single-user group."""
    group_ids = resolve_group_ids(user.id, apply_default_share=False)
    assert default_share_on.id not in group_ids
    assert group_ids, "expected the uploader's single-user group to remain"
