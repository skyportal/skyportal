"""Labelling an obj for the groups a deleted classification belonged to."""

import asyncio

from skyportal.handlers.api.source_labels import add_source_labels
from skyportal.models import ACL, GroupUser, User


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)

    def unique(self):
        return self

    def all(self):
        return self._rows


class _Label:
    def __init__(self, group_id):
        self.group_id = group_id


class _Session:
    """Records the reads so a test can count them, and the labels added."""

    # The access-controlled select type-checks this.
    user_or_token = User(id=73)

    def __init__(self, already_labelled=(), member_of=range(12)):
        self.reads = 0
        self.added = []
        self._rows = [_Label(g) for g in already_labelled]
        self._member_of = list(member_of)

    async def scalars(self, stmt):
        self.reads += 1
        if stmt.column_descriptions[0]["entity"] is GroupUser:
            return _Result(self._member_of)
        return _Result(self._rows)

    def add(self, obj):
        self.added.append(obj)


def test_one_read_however_many_groups():
    # The delete that reported this asked once per group, twelve groups deep.
    session = _Session()
    asyncio.run(add_source_labels(session, "ZTF26abc", list(range(12)), labeller_id=73))
    assert session.reads == 1
    assert [label.group_id for label in session.added] == list(range(12))


def test_a_group_already_labelled_is_left_alone():
    session = _Session(already_labelled=(2, 4))
    asyncio.run(add_source_labels(session, "ZTF26abc", [1, 2, 3, 4], labeller_id=73))
    assert [label.group_id for label in session.added] == [1, 3]


def test_a_repeated_group_is_labelled_once():
    session = _Session()
    asyncio.run(add_source_labels(session, "ZTF26abc", [5, 5, 6], labeller_id=73))
    assert [label.group_id for label in session.added] == [5, 6]


def test_no_groups_reads_nothing():
    session = _Session()
    asyncio.run(add_source_labels(session, "ZTF26abc", [], labeller_id=73))
    assert session.reads == 0 and session.added == []


def test_a_group_the_labeller_is_not_in_is_skipped():
    # A label there fails SourceLabel.create and rolls back the whole request.
    session = _Session(member_of=(1, 3))
    asyncio.run(
        add_source_labels(
            session, "ZTF26abc", [1, 2, 3], labeller_id=73, labeller_groups_only=True
        )
    )
    assert [label.group_id for label in session.added] == [1, 3]


def test_a_system_admin_labels_every_group():
    session = _Session(member_of=())
    session.user_or_token = User(id=73, acls=[ACL(id="System admin")])
    asyncio.run(
        add_source_labels(
            session, "ZTF26abc", [1, 2], labeller_id=73, labeller_groups_only=True
        )
    )
    assert session.reads == 1
    assert [label.group_id for label in session.added] == [1, 2]
