from skyportal.utils import data_access


def test_default_share_public_group_name_off(monkeypatch):
    # When the config flag is unset, uploads with no groups default to the
    # uploader only (no extra group).
    monkeypatch.setattr(
        data_access,
        "cfg",
        {
            "misc.share_data_with_public_group_by_default": False,
            "misc.public_group_name": "Sitewide Group",
        },
    )
    assert data_access.default_share_public_group_name() is None


def test_default_share_public_group_name_on(monkeypatch):
    # When set, the sitewide public group is the default extra share target.
    monkeypatch.setattr(
        data_access,
        "cfg",
        {
            "misc.share_data_with_public_group_by_default": True,
            "misc.public_group_name": "Sitewide Group",
        },
    )
    assert data_access.default_share_public_group_name() == "Sitewide Group"
