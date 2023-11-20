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
    'ls',
    'ps1',
    "new_gz",
    'ref_gz',
    'sub_gz',
)
INSTRUMENT_TYPES = ('imager', 'spectrograph', 'imaging spectrograph')
MMA_DETECTOR_TYPES = ('gravitational-wave', 'neutrino', 'gamma-ray-burst')
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
DEFAULT_ANALYSIS_FILTER_TYPES = {'classifications': ['name', 'probability']}
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
ALLOWED_ALLOCATION_TYPES = (
    "triggered",
    "forced_photometry",
    "observation_plan",
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

allowed_allocation_types = sa.Enum(
    *ALLOWED_ALLOCATION_TYPES, name='allocationtypes', validate_strings=True
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
mma_detector_types = sa.Enum(
    *MMA_DETECTOR_TYPES, name='mma_detector_types', validate_strings=True
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
    mma_detector_types,
    followup_priorities,
    api_classnames,
    listener_classnames,
    allowed_analysis_types,
    allowed_analysis_input_types,
    allowed_external_authentication_types,
    allowed_webbook_status_types,
]

GCN_NOTICE_TYPES = tuple(cfg.get('gcn.notice_types', []))
GCN_ACKNOWLEDGEMENTS = tuple(
    text.strip('"') if text is not None else text
    for text in cfg.get('gcn.summary.acknowledgements', [])
)

COLOR_PALETTE = [
    "#30123b",
    "#311542",
    "#32184a",
    "#341b51",
    "#351e58",
    "#36215f",
    "#372365",
    "#38266c",
    "#392972",
    "#3a2c79",
    "#3b2f7f",
    "#3c3285",
    "#3c358b",
    "#3d3791",
    "#3e3a96",
    "#3f3d9c",
    "#4040a1",
    "#4043a6",
    "#4145ab",
    "#4148b0",
    "#424bb5",
    "#434eba",
    "#4350be",
    "#4353c2",
    "#4456c7",
    "#4458cb",
    "#455bce",
    "#455ed2",
    "#4560d6",
    "#4563d9",
    "#4666dd",
    "#4668e0",
    "#466be3",
    "#466de6",
    "#4670e8",
    "#4673eb",
    "#4675ed",
    "#4678f0",
    "#467af2",
    "#467df4",
    "#467ff6",
    "#4682f8",
    "#4584f9",
    "#4587fb",
    "#4589fc",
    "#448cfd",
    "#438efd",
    "#4291fe",
    "#4193fe",
    "#4096fe",
    "#3f98fe",
    "#3e9bfe",
    "#3c9dfd",
    "#3ba0fc",
    "#39a2fc",
    "#38a5fb",
    "#36a8f9",
    "#34aaf8",
    "#33acf6",
    "#31aff5",
    "#2fb1f3",
    "#2db4f1",
    "#2bb6ef",
    "#2ab9ed",
    "#28bbeb",
    "#26bde9",
    "#25c0e6",
    "#23c2e4",
    "#21c4e1",
    "#20c6df",
    "#1ec9dc",
    "#1dcbda",
    "#1ccdd7",
    "#1bcfd4",
    "#1ad1d2",
    "#19d3cf",
    "#18d5cc",
    "#18d7ca",
    "#17d9c7",
    "#17dac4",
    "#17dcc2",
    "#17debf",
    "#18e0bd",
    "#18e1ba",
    "#19e3b8",
    "#1ae4b6",
    "#1be5b4",
    "#1de7b1",
    "#1ee8af",
    "#20e9ac",
    "#22eba9",
    "#24eca6",
    "#27eda3",
    "#29eea0",
    "#2cef9d",
    "#2ff09a",
    "#32f197",
    "#35f394",
    "#38f491",
    "#3bf48d",
    "#3ff58a",
    "#42f687",
    "#46f783",
    "#4af880",
    "#4df97c",
    "#51f979",
    "#55fa76",
    "#59fb72",
    "#5dfb6f",
    "#61fc6c",
    "#65fc68",
    "#69fd65",
    "#6dfd62",
    "#71fd5f",
    "#74fe5c",
    "#78fe59",
    "#7cfe56",
    "#80fe53",
    "#84fe50",
    "#87fe4d",
    "#8bfe4b",
    "#8efe48",
    "#92fe46",
    "#95fe44",
    "#98fe42",
    "#9bfd40",
    "#9efd3e",
    "#a1fc3d",
    "#a4fc3b",
    "#a6fb3a",
    "#a9fb39",
    "#acfa37",
    "#aef937",
    "#b1f836",
    "#b3f835",
    "#b6f735",
    "#b9f534",
    "#bbf434",
    "#bef334",
    "#c0f233",
    "#c3f133",
    "#c5ef33",
    "#c8ee33",
    "#caed33",
    "#cdeb34",
    "#cfea34",
    "#d1e834",
    "#d4e735",
    "#d6e535",
    "#d8e335",
    "#dae236",
    "#dde036",
    "#dfde36",
    "#e1dc37",
    "#e3da37",
    "#e5d838",
    "#e7d738",
    "#e8d538",
    "#ead339",
    "#ecd139",
    "#edcf39",
    "#efcd39",
    "#f0cb3a",
    "#f2c83a",
    "#f3c63a",
    "#f4c43a",
    "#f6c23a",
    "#f7c039",
    "#f8be39",
    "#f9bc39",
    "#f9ba38",
    "#fab737",
    "#fbb537",
    "#fbb336",
    "#fcb035",
    "#fcae34",
    "#fdab33",
    "#fda932",
    "#fda631",
    "#fda330",
    "#fea12f",
    "#fe9e2e",
    "#fe9b2d",
    "#fe982c",
    "#fd952b",
    "#fd9229",
    "#fd8f28",
    "#fd8c27",
    "#fc8926",
    "#fc8624",
    "#fb8323",
    "#fb8022",
    "#fa7d20",
    "#fa7a1f",
    "#f9771e",
    "#f8741c",
    "#f7711b",
    "#f76e1a",
    "#f66b18",
    "#f56817",
    "#f46516",
    "#f36315",
    "#f26014",
    "#f15d13",
    "#ef5a11",
    "#ee5810",
    "#ed550f",
    "#ec520e",
    "#ea500d",
    "#e94d0d",
    "#e84b0c",
    "#e6490b",
    "#e5460a",
    "#e3440a",
    "#e24209",
    "#e04008",
    "#de3e08",
    "#dd3c07",
    "#db3a07",
    "#d93806",
    "#d73606",
    "#d63405",
    "#d43205",
    "#d23005",
    "#d02f04",
    "#ce2d04",
    "#cb2b03",
    "#c92903",
    "#c72803",
    "#c52602",
    "#c32402",
    "#c02302",
    "#be2102",
    "#bb1f01",
    "#b91e01",
    "#b61c01",
    "#b41b01",
    "#b11901",
    "#ae1801",
    "#ac1601",
    "#a91501",
    "#a61401",
    "#a31201",
    "#a01101",
    "#9d1001",
    "#9a0e01",
    "#970d01",
    "#940c01",
    "#910b01",
    "#8e0a01",
    "#8b0901",
    "#870801",
    "#840701",
    "#810602",
    "#7d0502",
    "#7a0402",
]
