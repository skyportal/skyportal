#!/usr/bin/env python

from baselayer.app.models import Role
import datetime
from skyportal.models import init_db, User, UserACL, UserRole, DBSession
from baselayer.app.env import load_env


env, cfg = load_env()
init_db(**cfg["database"])

cutoff_datetime = datetime.datetime.now() + datetime.timedelta(days=1)
expired_users = (
    DBSession().query(User).filter(User.expiration_date < cutoff_datetime).all()
)

for user in expired_users:
    # Delete all existing roles and set to view only
    UserRole.query.filter(UserRole.user_id == user.id).delete()
    user.roles = [DBSession().query(Role).get("View only")]

    # Delete all of user's ACLs
    UserACL.query.filter(UserACL.user_id == user.id).delete()

DBSession.commit()

print(f"Set {len(expired_users)} users to view-only.")
