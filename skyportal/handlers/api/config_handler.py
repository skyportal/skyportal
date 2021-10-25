from baselayer.app.env import load_env
from baselayer.app.access import auth_or_token
from ..base import BaseHandler

from ...enum_types import default_spectrum_type, ALLOWED_SPECTRUM_TYPES

from skyportal.models import cosmo

_, cfg = load_env()


class ConfigHandler(BaseHandler):
    @auth_or_token
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
                            cosmology:
                                type: string
                                description: Details of the cosmology used here
                            cosmoref:
                                type: string
                                description: Reference for the cosmology used.
                            allowedSpectrumTypes:
                              type: array
                              description: allowed values for spectrum type.
                            defaultSpectrumType:
                              type: string
                              description: assigned to any spectrum posted without a type.
        """

        return self.success(
            data={
                "slackPreamble": cfg.get(
                    "slack.expected_url_preamble", "https://hooks.slack.com/"
                ),
                "invitationsEnabled": cfg["invitations.enabled"],
                "cosmology": str(cosmo),
                "cosmoref": cosmo.__doc__,
                "allowedSpectrumTypes": ALLOWED_SPECTRUM_TYPES,
                "defaultSpectrumType": default_spectrum_type,
            }
        )
