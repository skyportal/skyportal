# Baselayer models
from baselayer.app.models import *

# SkyPortal models
from .allocation import *
from .analysis import *
from .annotation import *
from .assignment import *
from .candidate import *
from .classification import *
from .comment import *
from .earthquake import *
from .facility_transaction import *
from .filter import *
from .followup_request import *
from .galaxy import *
from .gcn import *
from .group import *
from .group_joins import *
from .instrument import *
from .invitation import *
from .listing import *
from .localization import *
from .mmadetector import *
from .obj import *
from .observation import *
from .observation_plan import *
from .observing_run import *
from .photometry import *
from .photometry_validation import *
from .photometric_series import *
from .phot_stat import *
from .recurring_api import *
from .reminder import *
from .shift import *
from .source import *
from .source_label import *
from .source_view import *
from .source_notification import *
from .spatial_catalog import *
from .spectrum import *
from .survey_efficiency import *
from .stream import *
from .taxonomy import *
from .telescope import *
from .tns import *
from .thumbnail import *
from .user_notification import *
from .user_token import *
from .weather import *
from .webhook import *
from .sources_confirmed_in_gcn import *
from .public_pages.public_source_page import *

# Cosmology
from .cosmo import cosmo

# Generated schema
from .schema import setup_schema

schema.setup_schema()
