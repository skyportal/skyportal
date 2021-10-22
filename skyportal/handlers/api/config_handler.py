from baselayer.app.env import load_env
from ..base import BaseHandler

from ...enum_types import default_spectrum_type, ALLOWED_SPECTRUM_TYPES

_, cfg = load_env()


class ConfigHandler(BaseHandler):
    def get(self):
        """
        ---
        description: Retrieve parts of the config file that are exposed to the user/browser
        tags:
          - config
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
                            slackPreamble:
                              type: string
                              description: |
                                URL preamble used for forwarding slack notifications.
                                The default is "https://hooks.slack.com/".
                            spectrum_types:
                              type: array
                              description: allowed values for spectrum type.
        """

        return self.success(
            data={
                "slackPreamble": cfg.get(
                    "slack.expected_url_preamble", "https://hooks.slack.com/"
                ),
                "invitationsEnabled": cfg["invitations.enabled"],
                "allowedSpectrumTypes": ALLOWED_SPECTRUM_TYPES,
                "defaultSpectrumType": default_spectrum_type,
            }
        )
