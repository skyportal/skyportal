import datetime
from .models import (
    DBSession,
    User,
    Group,
    GroupUser,
    GroupStream,
    Invitation,
    Role,
    Stream,
    StreamUser,
)
from baselayer.app.env import load_env


env, cfg = load_env()

USER_FIELDS = ["username", "email"]


def create_user(strategy, details, backend, uid, user=None, *args, **kwargs):
    invite_token = strategy.session_get("invite_token")

    existing_user = DBSession().query(User).filter(User.oauth_uid == uid).first()

    if cfg["invitations.enabled"]:

        if existing_user is None and invite_token is None:
            return
        elif existing_user is not None:
            return {"is_new": False, "user": existing_user}

        try:
            n_days = int(cfg["invitations.days_until_expiry"])
        except ValueError:
            return

        invitation = Invitation.query.filter(Invitation.token == invite_token).first()
        if invitation is None:
            return

        cutoff_datetime = datetime.datetime.now() - datetime.timedelta(days=n_days)
        if invitation.created_at < cutoff_datetime:
            return
        if invitation.used:
            return

        user = User(
            username=details["username"],
            contact_email=details["email"],
            first_name=details["first_name"],
            last_name=details["last_name"],
            oauth_uid=uid,
        )
        user.roles.append(Role.query.get("Full user"))
        DBSession().add(user)
        # Add single-user group
        DBSession().add(Group(name=user.username, users=[user], single_user_group=True))
        DBSession().commit()
        return {"is_new": True, "user": user}
    elif not cfg["invitations.enabled"] and not cfg["server.auth.debug_login"]:
        if existing_user is not None:
            return {"is_new": False, "user": existing_user}

        if user is not None:  # Matching user already exists
            return {"is_new": False, "user": user}

        # No matching user exists; create a new user
        fields = dict(
            (name, kwargs.get(name, details.get(name)))
            for name in backend.setting("USER_FIELDS", USER_FIELDS)
        )
        user = strategy.create_user(**fields, **{"oauth_uid": uid})
        # Add single-user group
        DBSession().add(Group(name=user.username, users=[user], single_user_group=True))
        DBSession().commit()
        return {"is_new": True, "user": user}
    elif existing_user is not None:
        return {"is_new": False, "user": existing_user}
    elif user is not None:
        return {"is_new": False, "user": user}


def get_username(strategy, details, backend, uid, user=None, *args, **kwargs):
    if 'username' not in backend.setting('USER_FIELDS', USER_FIELDS):
        return
    storage = strategy.storage

    existing_user = DBSession().query(User).filter(User.oauth_uid == uid).first()

    if not user and existing_user is None:
        email_as_username = strategy.setting('USERNAME_IS_FULL_EMAIL', False)
        if email_as_username and details.get('email'):
            username = details['email']
        else:
            username = details['username']

    elif existing_user is not None:
        return {"username": existing_user.username}
    else:
        username = storage.user.get_username(user)
    return {'username': username}


def setup_invited_user_permissions(strategy, uid, details, user, *args, **kwargs):
    if not cfg["invitations.enabled"]:
        return

    existing_user = DBSession().query(User).filter(User.oauth_uid == uid).first()

    invite_token = strategy.session_get("invite_token")
    if invite_token is None:
        return
    invitation = Invitation.query.filter(Invitation.token == invite_token).first()
    if invitation is None:
        return

    if invitation.used:
        return

    group_ids = [g.id for g in invitation.groups]

    existing_user_group_ids = [g.id for g in existing_user.groups]

    # grab stream_ids
    stream_ids = set()
    for group_id in group_ids:
        streams = (
            DBSession()
            .query(Stream)
            .join(GroupStream)
            .filter(GroupStream.group_id == group_id)
            .all()
        )
        for stream in streams:
            stream_ids.add(stream.id)

    # Add stream access to single user group
    single_user_group = (
        DBSession().query(Group).filter(Group.name == user.username).first()
    )
    for stream_id in stream_ids:
        DBSession.add(GroupStream(group_id=single_user_group.id, stream_id=stream_id))
        DBSession.add(StreamUser(stream_id=stream_id, user_id=user.id))

    # Add user to specified groups
    for group_id, admin in zip(group_ids, invitation.admin_for_groups):
        if group_id not in existing_user_group_ids:
            DBSession.add(GroupUser(user_id=user.id, group_id=group_id, admin=admin))

    # Add user to sitewide public group
    public_group = (
        DBSession()
        .query(Group)
        .filter(Group.name == cfg["misc"]["public_group_name"])
        .first()
    )
    if public_group is not None and public_group.id not in existing_user_group_ids:
        DBSession().add(GroupUser(group_id=public_group.id, user_id=user.id))

    invitation.used = True
    DBSession().commit()
