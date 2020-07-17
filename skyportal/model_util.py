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

all_acl_ids = ['Become user', 'Comment', 'Manage users', 'Manage sources',
               'Manage groups', 'Upload data', 'System admin', 'Post taxonomy',
               'Delete taxonomy', 'Classify']

role_acls = {
    'Super admin': all_acl_ids,
    'Group admin': ['Comment', 'Manage sources', 'Upload data', 'Post taxonomy',
                    'Manage users'],
    'Full user': ['Comment', 'Upload data'],
    'View only': []
}


def add_user(username, roles=[], auth=False):
    user = User.query.filter(User.username == username).first()
    if user is None:
        user = User(username=username)
        if auth:
            social = TornadoStorage.user.create_social_auth(
                user,
                user.username,
                'google-oauth2'
            )

    for rolename in roles:
        role = Role.query.get(rolename)
        if role not in user.roles:
            user.roles.append(role)

    DBSession().add(user)
    DBSession().commit()

    return User.query.filter(User.username == username).first()


def make_super_user(username):
    """Initializes a super user with full permissions."""
    setup_permissions()  # make sure permissions already exist
    add_user(username, roles=['Super admin'], auth=True)


def provision_token():
    """Provision an initial administrative token.
    """
    admin = add_user('provisioned_admin', roles=['Super admin'])
    token_name = 'Initial admin token'

    token = (
        Token.query
        .filter(Token.created_by == admin)
        .filter(Token.name == token_name)
    ).first()

    if token is None:
        token_id = create_token(['System admin'],
                                admin.id,
                                token_name)
        token = Token.query.get(token_id)

    return token


def setup_permissions():
    """Create default ACLs/Roles needed by application.

    If a given ACL or Role already exists, it will be skipped."""
    all_acls = [ACL.create_or_get(a) for a in all_acl_ids]
    DBSession().add_all(all_acls)
    DBSession().commit()

    for r, acl_ids in role_acls.items():
        role = Role.create_or_get(r)
        role.acls = [ACL.query.get(a) for a in acl_ids]
        DBSession().add(role)
    DBSession().commit()


def create_token(ACLs, user_id, name):
    t = Token(permissions=ACLs, name=name)
    u = User.query.get(user_id)
    u.tokens.append(t)
    t.created_by = u
    DBSession().add(u)
    DBSession().add(t)
    DBSession().commit()
    return t.id
