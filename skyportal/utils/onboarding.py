import datetime
from social_core.exceptions import AuthTokenError
from ..models import DBSession, User, Group, GroupUser, Invitation
from baselayer.app.env import load_env


env, cfg = load_env()

USER_FIELDS = ['username', 'email']


def create_user(strategy, details, backend, user=None, *args, **kwargs):
    invite_token = strategy.session_get("invite_token")

    if invite_token is not None:
        try:
            n_days = int(cfg["invitations.days_til_expiry"])
        except ValueError:
            raise ValueError(
                "Invalid (non-integer) value provided for "
                "invitations.days_til_expiry in config file."
            )
        invitation = Invitation.query.filter(Invitation.token == invite_token).first()
        if invitation is None:
            return

        cutoff_datetime = datetime.datetime.now() - datetime.timedelta(days=n_days)
        if invitation.created_at < cutoff_datetime:
            raise AuthTokenError("Invite token has expired.")
        user = User(
            username=details["username"],
            contact_email=details["email"],
            first_name=details["first_name"],
            last_name=details["last_name"],
        )
        DBSession().add(user)
        DBSession().commit()
    if cfg["server.auth.debug_login"] and user is None:  # Allow uninvited new auths
        fields = dict(
            (name, kwargs.get(name, details.get(name)))
            for name in backend.setting('USER_FIELDS', USER_FIELDS)
        )
        user = strategy.create_user(**fields)

    return {'is_new': True, 'user': user}


def setup_invited_user_permissions(strategy, uid, details, user, *args, **kwargs):
    invite_token = strategy.session_get("invite_token")

    invitation = Invitation.query.filter(Invitation.token == invite_token).first()
    if invitation is None:
        return

    group_ids = [g.id for g in invitation.groups]

    # Add user to specified groups
    for group_id, admin in zip(group_ids, invitation.admin_for_groups):
        DBSession.add(GroupUser(user_id=user.id, group_id=group_id, admin=admin))

    # Create single-user group
    DBSession().add(Group(name=user.username, users=[user], single_user_group=True))

    # Add user to sitewide public group
    public_group = Group.query.filter(
        Group.name == cfg["misc"]["public_group_name"]
    ).first()
    if public_group is not None:
        DBSession().add(GroupUser(group_id=public_group.id, user_id=user.id))

    DBSession().commit()
