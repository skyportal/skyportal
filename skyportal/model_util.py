import datetime
import os
from pathlib import Path
import shutil
import numpy as np
import pandas as pd

from baselayer.app.env import load_env
from baselayer.app.model_util import status, create_tables, drop_tables
from social_tornado.models import TornadoStorage
from skyportal.models import (init_db, Base, DBSession, ACL, Comment,
                              Instrument, Group, GroupUser, Photometry, Role,
                              Source, Spectrum, Telescope, Thumbnail, User,
                              Token)


def add_super_user(username):
    """Initializes a super user with full permissions."""
    setup_permissions()  # make sure permissions already exist
    super_user = User.query.filter(User.username == username).first()
    if super_user is None:
        super_user = User(username=username)
        social = TornadoStorage.user.create_social_auth(super_user,
                                                        super_user.username,
                                                        'google-oauth2')
    admin_role = Role.query.get('Super admin')
    if admin_role not in super_user.roles:
        super_user.roles.append(admin_role)
    DBSession().add(super_user)
    DBSession().commit()


def setup_permissions():
    """Create default ACLs/Roles needed by application.

    If a given ACL or Role already exists, it will be skipped."""
    all_acl_ids = ['Become user', 'Comment', 'Manage users', 'Manage sources',
                   'Manage groups', 'Upload data', 'System admin']
    all_acls = [ACL.create_or_get(a) for a in all_acl_ids]
    DBSession().add_all(all_acls)
    DBSession().commit()

    role_acls = {
        'Super admin': all_acl_ids,
        'Group admin': ['Comment', 'Manage sources', 'Upload data'],
        'Full user': ['Comment', 'Upload data'],
        'View only': []
    }

    for r, acl_ids in role_acls.items():
        role = Role.create_or_get(r)
        role.acls = [ACL.query.get(a) for a in acl_ids]
        DBSession().add(role)
    DBSession().commit()


def create_token(permissions, created_by_id, name):
    t = Token(permissions=permissions, name=name)
    u = User.query.get(created_by_id)
    u.tokens.append(t)
    t.created_by = u
    DBSession().add(u)
    DBSession().add(t)
    DBSession().commit()
    return t.id
