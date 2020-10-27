from social_tornado.models import TornadoStorage
from skyportal.models import DBSession, ACL, User, Group, Token
from skyportal.enum_types import LISTENER_CLASSES
from baselayer.app.env import load_env

all_acl_ids = [
    'Become user',
    'Comment',
    'Annotate',
    'Manage users',
    'Manage sources',
    'Manage groups',
    'Manage allocations',
    'Upload data',
    'System admin',
    'Post taxonomy',
    'Delete taxonomy',
    'Classify',
] + [c.get_acl_id() for c in LISTENER_CLASSES]


role_acls = {
    'Super admin': all_acl_ids,
    'Group admin': [
        'Comment',
        'Manage sources',
        'Upload data',
        'Post taxonomy',
        'Manage users',
        'Classify',
    ],
    'Full user': ['Comment', 'Upload data', 'Classify'],
    'View only': [],
}

env, cfg = load_env()


def add_user(username, roles=[], acls=[], oauth_uid=None, auth=False):
    user = User.query.filter(User.username == username).first()
    if user is None:
        user = User(username=username, oauth_uid=oauth_uid)
        if auth:
            TornadoStorage.user.create_social_auth(user, user.username, 'google-oauth2')
    if not acls:
        for role in roles:
            acls.extend(role_acls[role])
    # Deduplicate
    acls = list(set(acls))
    acls = ACL.query.filter(ACL.id.in_(acls)).all()

    DBSession().add(user)
    DBSession().flush()

    user.acls = acls

    # Add user to sitewide public group
    public_group = Group.query.filter(
        Group.name == cfg["misc"]["public_group_name"]
    ).first()
    if public_group is None:
        public_group = Group(name=cfg["misc"]["public_group_name"])
        DBSession().add(public_group)
        DBSession().flush()

    user.groups.append(public_group)
    DBSession().commit()

    return User.query.get(user.id)


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
        Token.query.filter(Token.created_by == admin).filter(Token.name == token_name)
    ).first()

    if token is None:
        token_id = create_token(all_acl_ids, user_id=admin.id, name=token_name)
        token = Token.query.get(token_id)

    return token


def provision_public_group():
    """If public group name is set in the config file, create it."""
    env, cfg = load_env()
    public_group_name = cfg['misc.public_group_name']
    if public_group_name:
        pg = Group.query.filter(Group.name == public_group_name).first()

        if pg is None:
            DBSession().add(Group(name=public_group_name))
            DBSession().commit()


def setup_permissions():
    """Create default ACLs needed by application.

    If a given ACL already exists, it will be skipped."""
    all_acls = [ACL.create_or_get(a) for a in all_acl_ids]
    DBSession().add_all(all_acls)
    DBSession().commit()


def create_token(ACLs, user_id, name):
    acls = ACL.query.filter(ACL.id.in_(ACLs)).all()
    t = Token(acls=acls, name=name)
    u = User.query.get(user_id)
    u.tokens.append(t)
    t.created_by = u
    DBSession().add(u)
    DBSession().add(t)
    DBSession().commit()
    return t.id
