from ..models import DBSession, User
from .base import BaseHandler


class BecomeUserHandler(BaseHandler):
    def get(self, new_user_id: str | None = None):
        if not (
            self.cfg["server.auth.debug_login"]
            or {"System admin", "Become user"}.intersection(
                set(self.current_user.permissions)
            )
        ):
            return self.error("Insufficient permissions")

        user = DBSession().get(User, new_user_id)
        if user is None:
            return self.error("Invalid user ID.")

        sa = user.social_auth.first()
        self.clear_cookie("user_id")
        self.clear_cookie("user_oauth_uid")
        self.clear_cookie("auth_token")
        self.set_secure_cookie("user_id", new_user_id.encode("ascii"))
        # baselayer ignores the session unless both cookies are set, and machine
        # generated users have no social auth row to take a uid from.
        self.set_secure_cookie(
            "user_oauth_uid", (sa.uid if sa is not None else user.username).encode()
        )
        return self.success()
