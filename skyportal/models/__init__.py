# Monkey-patch matplotlib for simsurvey compatibility with matplotlib >= 3.8
# simsurvey imports matplotlib.docstring which was renamed to matplotlib._docstring
import matplotlib

if not hasattr(matplotlib, "docstring"):
    matplotlib.docstring = matplotlib._docstring

# Register numpy types with psycopg2 for numpy 2.x compatibility
# numpy 2 scalars no longer inherit from Python builtins, so psycopg2
# needs explicit adapters to serialize them in SQL parameters
import numpy as np
from psycopg2.extensions import AsIs, register_adapter


def _adapt_numpy_scalar(val):
    return AsIs(repr(float(val)))


for _np_type in [np.float64, np.float32, np.int64, np.int32, np.bool_]:
    register_adapter(_np_type, _adapt_numpy_scalar)

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
from .cosmo import cosmo
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
from .phot_stat import *
from .photometric_series import *
from .photometry import *
from .photometry_validation import *
from .public_pages.public_release import *
from .public_pages.public_source_page import *
from .recurring_api import *
from .reminder import *
from .scan_report.scan_report import *
from .scan_report.scan_report_item import *
from .schema import setup_schema
from .sharing_service import *
from .shift import *
from .source import *
from .source_label import *
from .source_notification import *
from .source_view import *
from .sources_confirmed_in_gcn import *
from .spatial_catalog import *
from .spectrum import *
from .stream import *
from .super_obj import *
from .survey_efficiency import *
from .tag import *
from .taxonomy import *
from .telescope import *
from .thumbnail import *
from .user_notification import *
from .user_token import *
from .weather import *
from .webhook import *

schema.setup_schema()
