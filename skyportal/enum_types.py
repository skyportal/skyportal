import astropy.units as u
import inspect
import numpy as np
import sncosmo
from sncosmo.bandpasses import _BANDPASSES
from sncosmo.magsystems import _MAGSYSTEMS
import sqlalchemy as sa

from enum import Enum
from baselayer.app.env import load_env
from baselayer.log import make_log
from . import facility_apis

log = make_log('enum_types')

_, cfg = load_env()

# load additional bandpasses into the SN comso registry
existing_bandpasses_names = [val['name'] for val in _BANDPASSES.get_loaders_metadata()]
additional_bandpasses_names = []
for additional_bandpasses in cfg.get('additional_bandpasses', []):
    name = additional_bandpasses.get("name")
    if not name:
        continue
    if name in existing_bandpasses_names:
        log(
            f"Additional Bandpass name={name} is already in the sncosmo registry. Skipping."
        )
    try:
        wavelength = np.array(additional_bandpasses.get("wavelength"))
        transmission = np.array(additional_bandpasses.get("transmission"))
        band = sncosmo.Bandpass(wavelength, transmission, name=name, wave_unit=u.AA)
    except Exception as e:
        log(f"Could not make bandpass for {name}: {e}")
        continue

    sncosmo.registry.register(band)
    additional_bandpasses_names.append(name)
    log(f"added custom bandpass '{name}'")


def force_render_enum_markdown(values):
    return ', '.join(list(map(lambda v: f'`{v}`', values)))


ALLOWED_SPECTRUM_TYPES = tuple(cfg['spectrum_types.types'])
ALLOWED_MAGSYSTEMS = tuple(val['name'] for val in _MAGSYSTEMS.get_loaders_metadata())
# though in the registry, the additional bandpass names are not in the _BANDPASSES list
ALLOWED_BANDPASSES = tuple(existing_bandpasses_names + additional_bandpasses_names)
TIME_STAMP_ALIGNMENT_TYPES = ('start', 'middle', 'end')

THUMBNAIL_TYPES = (
    'new',
    'ref',
    'sub',
    'sdss',
    'dr8',
    'ps1',
    "new_gz",
    'ref_gz',
    'sub_gz',
)
INSTRUMENT_TYPES = ('imager', 'spectrograph', 'imaging spectrograph')
FOLLOWUP_PRIORITIES = ('1', '2', '3', '4', '5')
FOLLOWUP_HTTP_REQUEST_ORIGINS = ('remote', 'skyportal')
LISTENER_CLASSNAMES = [
    k
    for k, v in facility_apis.__dict__.items()
    if inspect.isclass(v)
    and issubclass(v, facility_apis.Listener)
    and v is not facility_apis.Listener
]

LISTENER_CLASSES = [getattr(facility_apis, c) for c in LISTENER_CLASSNAMES]

ANALYSIS_TYPES = ('lightcurve_fitting', 'spectrum_fitting', 'meta_analysis')
ANALYSIS_INPUT_TYPES = (
    'photometry',
    'spectra',
    'redshift',
    'annotations',
    'comments',
    'classifications',
)
AUTHENTICATION_TYPES = (
    'none',
    'header_token',
    'api_key',
    'HTTPBasicAuth',
    'HTTPDigestAuth',
    'OAuth1',
)
WEBHOOK_STATUS_TYPES = (
    'queued',
    'pending',
    'completed',
    'failure',
    'cancelled',
    'timed_out',
)
allowed_webbook_status_types = sa.Enum(
    *WEBHOOK_STATUS_TYPES, name='webhookstatustypes', validate_strings=True
)

allowed_analysis_types = sa.Enum(
    *ANALYSIS_TYPES, name='analysistypes', validate_strings=True
)

allowed_analysis_input_types = sa.Enum(
    *ANALYSIS_INPUT_TYPES, name='analysisinputtypes', validate_strings=True
)

allowed_external_authentication_types = sa.Enum(
    *AUTHENTICATION_TYPES, name='authenticationtypes', validate_strings=True
)

allowed_spectrum_types = sa.Enum(
    *ALLOWED_SPECTRUM_TYPES, name='spectrumtypes', validate_strings=True
)
default_spectrum_type = cfg['spectrum_types.default']

allowed_magsystems = sa.Enum(
    *ALLOWED_MAGSYSTEMS, name="magsystems", validate_strings=True
)
allowed_bandpasses = sa.Enum(
    *ALLOWED_BANDPASSES, name="bandpasses", validate_strings=True
)
time_stamp_alignment_types = sa.Enum(
    *TIME_STAMP_ALIGNMENT_TYPES, name='time_stamp_alignments', validate_strings=True
)
thumbnail_types = sa.Enum(
    *THUMBNAIL_TYPES, name='thumbnail_types', validate_strings=True
)
instrument_types = sa.Enum(
    *INSTRUMENT_TYPES, name='instrument_types', validate_strings=True
)

followup_priorities = sa.Enum(
    *FOLLOWUP_PRIORITIES, name='followup_priorities', validate_strings=True
)

ALLOWED_API_CLASSNAMES = [
    k
    for k, v in facility_apis.__dict__.items()
    if inspect.isclass(v)
    and issubclass(v, facility_apis.FollowUpAPI)
    and v is not facility_apis.FollowUpAPI
]

api_classnames = sa.Enum(
    *ALLOWED_API_CLASSNAMES,
    name='followup_apis',
    validate_strings=True,
)

listener_classnames = sa.Enum(
    *LISTENER_CLASSNAMES,
    name='followup_listeners',
    validate_strings=True,
)

py_allowed_spectrum_types = Enum('spectrumtypes', ALLOWED_SPECTRUM_TYPES)
py_allowed_magsystems = Enum('magsystems', ALLOWED_MAGSYSTEMS)
py_allowed_bandpasses = Enum('bandpasses', ALLOWED_BANDPASSES)
py_thumbnail_types = Enum('thumbnail_types', THUMBNAIL_TYPES)
py_followup_priorities = Enum('priority', FOLLOWUP_PRIORITIES)
py_allowed_analysis_types = Enum('analysistypes', ANALYSIS_TYPES)
py_allowed_analysis_input_types = Enum('analysisinputtypes', ANALYSIS_INPUT_TYPES)
py_allowed_external_authentication_types = Enum(
    'authenticationtypes', AUTHENTICATION_TYPES
)
py_allowed_webbook_status_types = Enum('webhookstatustypes', WEBHOOK_STATUS_TYPES)


sqla_enum_types = [
    allowed_spectrum_types,
    allowed_bandpasses,
    thumbnail_types,
    instrument_types,
    followup_priorities,
    api_classnames,
    listener_classnames,
    allowed_analysis_types,
    allowed_analysis_input_types,
    allowed_external_authentication_types,
    allowed_webbook_status_types,
]

GCN_NOTICE_TYPES = tuple(cfg.get('gcn.notice_types', []))
