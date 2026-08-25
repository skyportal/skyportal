import uuid

import pytest

from skyportal.models import DBSession, User
from skyportal.onboarding import get_unique_username


@pytest.fixture()
def usernames_in_use():
    created = []

    def _create(*usernames):
        for username in usernames:
            user = User(username=username)
            DBSession().add(user)
            created.append(user)
        DBSession().commit()

    yield _create

    for user in created:
        DBSession().delete(user)
    DBSession().commit()


def test_get_unique_username_keeps_free_base(usernames_in_use):
    base = f"onboard{uuid.uuid4().hex[:8]}"
    assert get_unique_username(base) == base


def test_get_unique_username_appends_counter(usernames_in_use):
    base = f"onboard{uuid.uuid4().hex[:8]}"
    usernames_in_use(base)
    assert get_unique_username(base) == f"{base}1"


def test_get_unique_username_skips_taken_counters(usernames_in_use):
    base = f"onboard{uuid.uuid4().hex[:8]}"
    usernames_in_use(base, f"{base}1", f"{base}2")
    assert get_unique_username(base) == f"{base}3"


def test_get_unique_username_ignores_unrelated_prefix_matches(usernames_in_use):
    base = f"onboard{uuid.uuid4().hex[:8]}"
    usernames_in_use(f"{base}smith")
    assert get_unique_username(base) == base
