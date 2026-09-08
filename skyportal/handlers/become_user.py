from ..models import DBSession, User
from .base import BaseHandler


class BecomeUserHandler(BaseHandler):
    def get(self, new_user_id: str | None = None):
        if not (
            self.cfg["server.auth.debug_login"]
            or {"System admin", "Become user"}.intersection(
                self.current_user.permissions
            )
        ):
            return self.error("Insufficient permissions")

        user = DBSession().get(User, new_user_id)
        if user is None:
            return self.error("Invalid user ID.")

        self.clear_cookie("auth_token")
        self.set_secure_cookie("user_id", new_user_id.encode("ascii"))
        # baselayer ignores the session unless both cookies are set.
        sa = user.social_auth.first()
        self.set_secure_cookie(
            "user_oauth_uid", (sa.uid if sa else user.username).encode()
        )
        return self.success()
