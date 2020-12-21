import pytest
from skyportal.models import Base, User, DBSession

subclasses = Base.__subclasses__()
access_types = ['create', 'read', 'update', 'delete']
parameters = [(c, m) for c in subclasses for m in access_types]


@pytest.mark.parametrize("cls,mode", parameters)
def test_return_type(cls, mode):
    DBSession().rollback()
    q = cls.accessibility_query(User.id, mode=mode)
    for instance, user, is_accessible in q:
        assert type(instance.is_accessible_by(user, mode=mode)) is bool
        assert type(is_accessible) is bool


@pytest.mark.parametrize("cls,mode", parameters)
def test_scalar_vector_consistency(cls, mode):
    DBSession().rollback()
    q = cls.accessibility_query(User.id, mode=mode)
    for instance, user, is_accessible in q:
        assert instance.is_accessible_by(user, mode=mode) == is_accessible


@pytest.mark.parametrize("cls,mode", parameters)
def test_filter_by_accessibility(cls, mode):
    DBSession().rollback()
    q = cls.accessibility_query(User.id, mode=mode)
    accessible = q.accessibility_target
    q = q.filter(accessible)
    for instance, user, is_accessible in q:
        assert instance.is_accessible_by(user, mode=mode) == is_accessible
