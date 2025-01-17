from ..models import User
from .base import BaseHandler


class BecomeUserHandler(BaseHandler):
    def get(self, new_user_id=None):
        if not (
            self.cfg["server.auth.debug_login"]
            or {"System admin", "Become user"}.intersection(
                set(self.current_user.permissions)
            )
        ):
            return self.error("Insufficient permissions")

        user = User.query.get(new_user_id)
        if user is None:
            return self.error("Invalid user ID.")

        sa = user.social_auth.first()
        self.clear_cookie("user_id")
        self.clear_cookie("user_oauth_id")
        self.clear_cookie("auth_token")
        self.set_secure_cookie("user_id", new_user_id.encode("ascii"))
        if sa is not None:
            self.set_secure_cookie("user_oauth_id", sa.uid.encode("ascii"))
        return self.success()
