from baselayer.app.env import load_env
from baselayer.app.access import auth_or_token
from ..base import BaseHandler


_, cfg = load_env()


class SysInfoHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve system/deployment info
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
                          invitationsEnabled:
                            type: boolean
                          description: |
                            Boolean indicating whether new user invitation pipeline
                            is enabled in current deployment.
        """
        return self.success(data={"invitationsEnabled": cfg["invitations.enabled"]})
