import datetime
from slugify import slugify

from .models import (
    DBSession,
    ACL,
    User,
    Group,
    GroupUser,
    Invitation,
    StreamUser,
)
from .model_util import role_acls
from baselayer.app.env import load_env


env, cfg = load_env()

USER_FIELDS = ["username", "email"]


def create_user(strategy, details, backend, uid, user=None, *args, **kwargs):
    invite_token = strategy.session_get("invite_token")

    existing_user = DBSession().query(User).filter(User.oauth_uid == uid).first()

    if cfg["invitations.enabled"]:

        if existing_user is None and invite_token is None:
            raise Exception("Missing invite token. A valid invite token is required.")
        elif existing_user is not None:
            return {"is_new": False, "user": existing_user}

        try:
            n_days = int(cfg["invitations.days_until_expiry"])
        except ValueError:
            raise ValueError(
                "Invalid invitation configuration value: invitations.days_until_expiry cannot be cast to int"
            )

        invitation = Invitation.query.filter(Invitation.token == invite_token).first()
        if invitation is None:
            raise Exception("Invalid invite token. A valid invite token is required.")

        cutoff_datetime = datetime.datetime.now() - datetime.timedelta(days=n_days)
        if invitation.created_at < cutoff_datetime:
            raise Exception("Invite token expired.")
        if invitation.used:
            raise Exception("Invite token has already been used.")

        user = User(
            username=details["username"],
            contact_email=details["email"],
            first_name=details["first_name"],
            last_name=details["last_name"],
            oauth_uid=uid,
            acls=ACL.query.filter(ACL.id.in_(role_acls["Full user"])).all(),
        )
        DBSession().add(user)
        # Add single-user group
        DBSession().add(
            Group(name=slugify(user.username), users=[user], single_user_group=True)
        )
        DBSession().commit()
        return {"is_new": True, "user": user}
    elif not cfg["invitations.enabled"]:
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
        raise Exception("PSA configuration error: `username` not properly captured.")
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
    if invite_token is None and existing_user is None:
        raise Exception("Missing invite token. A valid invite token is required.")
    elif existing_user is not None and invite_token is None:
        return

    invitation = Invitation.query.filter(Invitation.token == invite_token).first()
    if invitation is None:
        raise Exception("Invalid invite token. A valid invite token is required.")

    if invitation.used:
        raise Exception("Invitation has already been used.")

    group_ids = [g.id for g in invitation.groups]
    stream_ids = [stream.id for stream in invitation.streams]

    if not all(
        [
            stream in invitation.streams
            for group in invitation.groups
            for stream in group.streams
        ]
    ):
        raise Exception(
            "User has not been granted sufficient stream access to be added "
            "to specified groups."
        )

    # Add user to specified streams
    for stream_id in stream_ids:
        DBSession.add(StreamUser(stream_id=stream_id, user_id=user.id))

    # Add user to specified groups
    for group_id, admin in zip(group_ids, invitation.admin_for_groups):
        DBSession.add(GroupUser(user_id=user.id, group_id=group_id, admin=admin))

    # Add user to sitewide public group
    public_group = (
        DBSession()
        .query(Group)
        .filter(Group.name == cfg["misc"]["public_group_name"])
        .first()
    )
    if public_group is not None and public_group not in invitation.groups:
        DBSession().add(GroupUser(group_id=public_group.id, user_id=user.id))

    invitation.used = True
    DBSession().commit()


def user_details(strategy, details, backend, uid, user=None, *args, **kwargs):
    """Update user details using data from provider."""
    if not user:
        return
    existing_user = DBSession().query(User).filter(User.oauth_uid == uid).first()
    if not (
        existing_user.contact_email is None
        and existing_user.first_name is None
        and existing_user.last_name is None
    ):
        return

    changed = False  # flag to track changes

    # Default protected user fields (username, id, pk and email) can be ignored
    # by setting the SOCIAL_AUTH_NO_DEFAULT_PROTECTED_USER_FIELDS to True
    if strategy.setting('NO_DEFAULT_PROTECTED_USER_FIELDS') is True:
        protected = ()
    else:
        protected = (
            'username',
            'id',
            'pk',
            'email',
            'password',
            'is_active',
            'is_staff',
            'is_superuser',
        )

    protected = protected + tuple(strategy.setting('PROTECTED_USER_FIELDS', []))

    # Update user model attributes with the new data sent by the current
    # provider. Update on some attributes is disabled by default, for
    # example username and id fields. It's also possible to disable update
    # on fields defined in SOCIAL_AUTH_PROTECTED_USER_FIELDS.
    field_mapping = strategy.setting('USER_FIELD_MAPPING', {}, backend)
    for name, value in details.items():
        # Convert to existing user field if mapping exists
        name = field_mapping.get(name, name)
        if value is None or not hasattr(user, name) or name in protected:
            continue

        current_value = getattr(user, name, None)
        if current_value == value:
            continue

        changed = True
        setattr(user, name, value)

    if changed:
        strategy.storage.user.changed(user)
