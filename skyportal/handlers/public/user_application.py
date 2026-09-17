from ...utils.user_applications import user_applications_enabled
from ..base import BaseHandler


class ApplyPageHandler(BaseHandler):
    """The account application form, served to people who have no account yet."""

    terms_of_service_exempt = ("GET",)

    def get(self):
        """
        ---
        summary: Display the account application form
        description: Display the form for applying for an account
        tags:
          - public
          - user_applications
        responses:
          200:
            content:
              text/html:
                schema:
                  type: string
        """
        if not user_applications_enabled():
            self.set_status(404)
            return self.render("login.html")
        return self.render("apply.html")
