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


def create_user(
    username,
    roles=[],
    auth=False,
    first_name=None,
    last_name=None,
    contact_email=None,
    contact_phone=None,
    expiration_date=None,
    add_to_public_group=True,
    session=None,
):
    """Create a user with the given roles."""
    if session is None:
        session = ThreadSession()
    user = session.scalars(sa.select(User).where(User.username == username)).first()
    if user is None:
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            expiration_date=expiration_date,
        )
        if auth is not None and auth is not False:
            if isinstance(bool(auth), bool):
                TornadoStorage.user.create_social_auth(
                    user, user.username, 'google-oauth2'
                )
            else:
                user.oauth_uid = auth

    session.add(user)
    session.flush()
    for rolename in roles:
        role = session.scalars(sa.select(Role).where(Role.id == rolename)).first()
        if role.id not in [r.id for r in user.roles]:
            user.roles.append(role)

    if add_to_public_group:
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

    return session.scalar(sa.select(User).where(User.username == username))


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
    create_user(username, roles=['Super admin'], auth=True)


def provision_token():
    """Provision an initial administrative token."""
    with ThreadSession() as session:
        admin = create_user(
            'provisioned_admin',
            roles=['Super admin'],
            first_name="provisioned",
            last_name="admin",
            session=session,
        )
        token_name = 'Initial admin token'
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
        all_acls = []
        for acl_id in all_acl_ids:
            acl = session.get(ACL, acl_id)
            if acl is None:
                acl = ACL(id=acl_id)
                session.add(acl)
            all_acls.append(acl)
        session.commit()

        for r, acl_ids in role_acls.items():
            role = session.get(Role, r)
            if role is None:
                role = Role(id=r)
            role.acls = [session.get(ACL, a) for a in acl_ids]
            session.add(role)
        session.commit()


def create_token(ACLs, user_id, name, session=None):
    if session is None:
        session = ThreadSession()
    """Create a token with the given ACLs for the given user."""
    ACLs = session.scalars(sa.select(ACL).where(ACL.id.in_(ACLs))).all()
    t = Token(name=name)
    session.add(t)
    for acl in ACLs:
        t.acls.append(acl)
    u = session.scalar(sa.select(User).where(User.id == user_id))
    u.tokens.append(t)
    t.created_by = u
    session.add(u)
    session.commit()
    return t.id


def delete_token(token_id, session=None):
    """Delete a token."""
    if session is None:
        session = ThreadSession()
    t = session.scalar(sa.select(Token).where(Token.id == token_id))
    if t is not None:
        session.delete(t)
        session.commit()
