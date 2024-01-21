import copy

from matplotlib.cm import get_cmap
from matplotlib.colors import rgb2hex

from baselayer.app.env import load_env
from baselayer.app.access import auth_or_token
from ..base import BaseHandler

from ...enum_types import (
    default_spectrum_type,
    ALLOWED_SPECTRUM_TYPES,
    GCN_NOTICE_TYPES,
    GCN_ACKNOWLEDGEMENTS,
    ALLOWED_ALLOCATION_TYPES,
)

from .recurring_api import ALLOWED_RECURRING_API_METHODS
from .source import MAX_NUM_DAYS_USING_LOCALIZATION
from skyportal.utils.tns import TNS_INSTRUMENT_IDS

from .photometry import BANDPASSES_COLORS
from .summary_query import USE_PINECONE

from skyportal.models import cosmo

_, cfg = load_env()

TNS_INSTRUMENTS = list(TNS_INSTRUMENT_IDS.keys())

cmap = get_cmap(cfg.get("misc.color_palette", "turbo"))

# we convert it to a list of hex colors
cmap = [rgb2hex(cmap(i)) for i in range(cmap.N)]


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
                            classificationsClasses:
                              type: object
                              description: allowed classifications classes.
        """
        openai_summary_parameters = copy.deepcopy(
            cfg["analysis_services.openai_analysis_service.summary"]
        )
        openai_summary_apikey_set = openai_summary_parameters.get("api_key") is not None
        openai_summary_parameters.pop("api_key", None)

        return self.success(
            data={
                "slackPreamble": cfg["slack.expected_url_preamble"],
                "invitationsEnabled": cfg["invitations.enabled"],
                "cosmology": str(cosmo),
                "openai_summary_apikey_set": openai_summary_apikey_set,
                "openai_summary_parameters": openai_summary_parameters,
                "cosmoref": cosmo.__doc__,
                "allowedAllocationTypes": ALLOWED_ALLOCATION_TYPES,
                "allowedSpectrumTypes": ALLOWED_SPECTRUM_TYPES,
                "defaultSpectrumType": default_spectrum_type,
                "gcnNoticeTypes": GCN_NOTICE_TYPES,
                "gcnSummaryAcknowledgements": GCN_ACKNOWLEDGEMENTS,
                "maxNumDaysUsingLocalization": MAX_NUM_DAYS_USING_LOCALIZATION,
                "image_analysis": True if 'image_analysis' in cfg else False,
                "allowedRecurringAPIMethods": ALLOWED_RECURRING_API_METHODS,
                "classificationsClasses": cfg["colors.classifications"],
                "summary_sourcesClasses": cfg["colors.summary_sources"],
                "tnsAllowedInstruments": TNS_INSTRUMENTS,
                "gcnTagsClasses": cfg["colors.gcnTags"],
                "colorPalette": cmap,
                "bandpassesColors": BANDPASSES_COLORS,
                "usePinecone": USE_PINECONE,
            }
        )
