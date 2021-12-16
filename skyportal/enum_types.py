import sqlalchemy as sa
from enum import Enum
import inspect
import numpy as np
from astropy import units as u, wcs

from baselayer.app.env import load_env

from . import facility_apis

from sncosmo.bandpasses import (
    Bandpass, _BANDPASSES, _BANDPASS_INTERPOLATORS, read_bandpass)
from sncosmo.magsystems import _MAGSYSTEMS

_, cfg = load_env()

def tophat_bandpass_um(ctr, width, name=None):
    """Create a tophat Bandpass centered at `ctr` with width `width` (both
    in microns)."""

    wave = np.array([ctr - width / 2.0, ctr + width / 2.0])
    trans = np.array([1.0, 1.0])
    return Bandpass(wave, trans, wave_unit=u.micron, name=name)


    trans = np.array([1.0, 1.0])
    return Bandpass(wave, trans, wave_unit=u.nano, name=name)

# GRANDMA FILTERS

# find values for C and w
grandmafilters_meta = {
    'filterset': 'grandma filters',
    'retrieved': '15 Nov 2021',
    'description': 'grandma filters from Alldata.txt'}
for name, ctr, width in [('grandma::B',  0.445, 0.01),
                    ('grandma::C',  0.01, 0.01),
                    ('grandma::G', 0.464, 0.01),
                    ('grandma::I', 0.806, 0.01),
                    ('grandma::L', 3.450, 0.01),
                    ('grandma::N', 10.5, 0.01),
                    ('grandma::R', 0.658, 0.01),
                    ('grandma::V', 0.551, 0.01),
                    ('grandma::w',  0.01, 0.01)]:
    _BANDPASSES.register_loader(name, tophat_bandpass_um,
                                args=(ctr, width), meta=grandmafilters_meta)

def force_render_enum_markdown(values):
    return ', '.join(list(map(lambda v: f'`{v}`', values)))

ALLOWED_SPECTRUM_TYPES = tuple(
    cfg.get('spectrum_types.types', ['source', 'host', 'host_center'])
)
ALLOWED_MAGSYSTEMS = tuple(val['name'] for val in _MAGSYSTEMS.get_loaders_metadata())
ALLOWED_BANDPASSES = tuple(val['name'] for val in _BANDPASSES.get_loaders_metadata())
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

allowed_spectrum_types = sa.Enum(
    *ALLOWED_SPECTRUM_TYPES, name='spectrumtypes', validate_strings=True
)
default_spectrum_type = cfg.get('spectrum_types.default', "source")

allowed_magsystems = sa.Enum(
    *ALLOWED_MAGSYSTEMS, name="magsystems", validate_strings=True
)
allowed_bandpasses = sa.Enum(
    *ALLOWED_BANDPASSES, name="bandpasses", validate_strings=True
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

api_classnames = sa.Enum(
    *[
        k
        for k, v in facility_apis.__dict__.items()
        if inspect.isclass(v)
        and issubclass(v, facility_apis.FollowUpAPI)
        and v is not facility_apis.FollowUpAPI
    ],
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

sqla_enum_types = [
    allowed_spectrum_types,
    allowed_bandpasses,
    thumbnail_types,
    instrument_types,
    followup_priorities,
    api_classnames,
    listener_classnames,
]
