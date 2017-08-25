import uuid
from skyportal.models import (DBSession, User, Source, Group, GroupUser,
                              GroupSource)
from tempfile import mkdtemp

import factory


TMP_DIR = mkdtemp()


class BaseMeta:
    sqlalchemy_session = DBSession()
    sqlalchemy_session_persistence = 'commit'


class GroupFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Group
    name = factory.LazyFunction(uuid.uuid4)

    @factory.post_generation
    def add_users(group, create, value, *args, **kwargs):
        group.users = list(User.query.filter(User.username ==
                                             "testuser@cesium-ml.org"))
        DBSession().commit()


class SourceFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseMeta):
        model = Source
    id = factory.LazyFunction(uuid.uuid4)
    ra = 0.0
    dec = 0.0
    red_shift = 0.0


#class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
#    class Meta(BaseMeta):
#        model = User
#
#    username = 'testuser@cesium-ml.org'
#
#    @classmethod
#    def _create(cls, model_class, *args, **kwargs):
#        """Get `User` if it already exists, otherwise create/add a new one."""
#        q = cls._meta.sqlalchemy_session.query(model_class)
#        for key, value in kwargs.items():
#            q = q.filter(getattr(model_class, key) == value)
#        obj = q.first()
#        if obj is None:
#            return super(UserFactory, cls)._create(model_class, *args, **kwargs)
#        else:
#            return obj
