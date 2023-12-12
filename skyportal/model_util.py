import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.psa import TornadoStorage
from skyportal.enum_types import LISTENER_CLASSES, sqla_enum_types
from skyportal.models import ThreadSession, ACL, Group, Role, Token, User

all_acl_ids = [
    'Become user',
    'Comment',
    'Annotate',
    'Manage users',
    'Manage sources',
    'Manage groups',
    'Manage shifts',
    'Manage instruments',
    'Manage allocations',
    'Manage observing runs',
    'Manage telescopes',
    'Manage Analysis Services',
    'Manage Recurring APIs',
    'Manage observation plans',
    'Manage GCNs',
    'Upload data',
    'Run Analyses',
    'System admin',
    'Post taxonomy',
    'Delete taxonomy',
    'Delete instrument',
    'Delete telescope',
    'Delete bulk photometry',
    'Classify',
] + [c.get_acl_id() for c in LISTENER_CLASSES]


role_acls = {
    'Super admin': all_acl_ids,
    'Group admin': [
        'Annotate',
        'Comment',
        'Manage shifts',
        'Manage sources',
        'Manage Analysis Services',
        'Manage Recurring APIs',
        'Manage GCNs',
        'Upload data',
        'Run Analyses',
        'Post taxonomy',
        'Manage users',
        'Classify',
        'Manage observing runs',
    ],
    'Full user': [
        'Annotate',
        'Comment',
        'Upload data',
        'Classify',
        'Run Analyses',
        'Manage observing runs',
    ],
    'View only': [],
}

env, cfg = load_env()


def add_user(username, roles=[], auth=False, first_name=None, last_name=None):

    with ThreadSession() as session:
        user = session.scalars(sa.select(User).where(User.username == username)).first()

        if user is None:
            user = User(username=username, first_name=first_name, last_name=last_name)
            if auth:
                TornadoStorage.user.create_social_auth(
                    user, user.username, 'google-oauth2'
                )

        for rolename in roles:
            role = session.scalars(sa.select(Role).where(Role.id == rolename)).first()
            if role not in user.roles:
                user.roles.append(role)

        session.add(user)
        session.flush()

        # Add user to sitewide public group
        public_group_name = cfg['misc.public_group_name']
        if public_group_name:
            public_group = session.scalars(
                sa.select(Group).where(Group.name == public_group_name)
            ).first()
            if public_group is None:
                public_group = Group(name=public_group_name)
                session.add(public_group)
                session.flush()

        user.groups.append(public_group)
        session.commit()

        return session.query(User).filter(User.username == username).first()


def refresh_enums():
    with ThreadSession() as session:
        for type in sqla_enum_types:
            for key in type.enums:
                session.execute(
                    sa.text(f"ALTER TYPE {type.name} ADD VALUE IF NOT EXISTS '{key}'")
                )
        session.commit()


def make_super_user(username):
    """Initializes a super user with full permissions."""
    setup_permissions()  # make sure permissions already exist
    add_user(username, roles=['Super admin'], auth=True)


def provision_token():
    """Provision an initial administrative token."""
    admin = add_user(
        'provisioned_admin',
        roles=['Super admin'],
        first_name="provisioned",
        last_name="admin",
    )
    token_name = 'Initial admin token'

    with ThreadSession() as session:
        token = session.scalar(
            sa.select(Token).where(
                Token.name == token_name, Token.created_by_id == admin.id
            )
        )
        if token is None:
            token_id = create_token(all_acl_ids, user_id=admin.id, name=token_name)
            token = session.get(Token, token_id)

        return token


def provision_public_group():
    """If public group name is set in the config file, create it."""
    env, cfg = load_env()
    public_group_name = cfg['misc.public_group_name']
    with ThreadSession() as session:
        pg = session.query(Group).filter(Group.name == public_group_name).first()
        if pg is None:
            session.add(Group(name=public_group_name))
            session.commit()


def setup_permissions():
    """Create default ACLs/Roles needed by application.

    If a given ACL or Role already exists, it will be skipped."""
    with ThreadSession() as session:
        all_acls = [ACL.create_or_get(a, session) for a in all_acl_ids]
        session.add_all(all_acls)
        session.commit()

        for r, acl_ids in role_acls.items():
            role = session.get(Role, r)
            if role is None:
                role = Role(id=r)
            role.acls = [session.get(ACL, a) for a in acl_ids]
            session.add(role)
        session.commit()


def create_token(ACLs, user_id, name):
    t = Token(permissions=ACLs, name=name)
    ThreadSession.add(t)
    u = ThreadSession().scalar(sa.select(User).where(User.id == user_id))
    u.tokens.append(t)
    t.created_by = u
    ThreadSession.add(u)
    ThreadSession.commit()
    return t.id


def delete_token(token_id):
    t = ThreadSession().scalar(sa.select(Token).where(Token.id == token_id))
    if t is not None:
        ThreadSession.delete(t)
        ThreadSession.commit()
