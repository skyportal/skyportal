from baselayer.app.env import load_env

_, cfg = load_env()

ENDORSE_ACL = "Endorse users"
ADMIN_ACL = "Manage users"


def user_applications_enabled() -> bool:
    """Whether people without an account may apply for one.

    Endorsing an application issues an invitation, so the feature is inert
    without the invitation pipeline.
    """
    return bool(cfg.get("user_applications.enabled", False)) and bool(
        cfg["invitations.enabled"]
    )


def deciding_acls() -> tuple[str, ...]:
    """The ACLs that let a user act on an application.

    Peer endorsement puts that in the hands of ordinary users alongside the
    administrators who can always do it; otherwise only administrators approve.
    """
    if cfg.get("user_applications.peer_endorsement", False):
        return (ENDORSE_ACL, ADMIN_ACL)
    return (ADMIN_ACL,)


def may_decide(user_or_token) -> bool:
    """Whether this user may endorse or decline applications."""
    if not user_applications_enabled():
        return False
    if user_or_token.is_system_admin:
        return True
    return bool(set(deciding_acls()) & {acl.id for acl in user_or_token.acls})
