from baselayer.app.access import auth_or_token

from ....utils.telegram import link_url, telegram_enabled
from ...base import BaseHandler


class TelegramLinkHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        summary: Get a link that connects your Telegram account
        description: |
          Opening the link starts a chat with the instance's Telegram bot,
          which then sends your notifications to that chat. It expires after an hour.
        tags:
          - users
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            url:
                              type: string
          400:
            content:
              application/json:
                schema: Error
        """
        if not telegram_enabled():
            return self.error("Telegram notifications are not configured")
        try:
            url = link_url(self.associated_user_object.id)
        except Exception as e:
            return self.error(f"Could not reach Telegram: {e}")
        return self.success(data={"url": url})
