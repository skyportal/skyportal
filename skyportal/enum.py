import sqlalchemy as sa
from enum import Enum

from sncosmo.bandpasses import _BANDPASSES
from sncosmo.magsystems import _MAGSYSTEMS

ALLOWED_MAGSYSTEMS = tuple(l['name'] for l in _MAGSYSTEMS.get_loaders_metadata())
ALLOWED_BANDPASSES = tuple(l['name'] for l in _BANDPASSES.get_loaders_metadata())
THUMBNAIL_TYPES = ('new', 'ref', 'sub', 'sdss', 'dr8', "new_gz", 'ref_gz', 'sub_gz')

allowed_magsystems = sa.Enum(*ALLOWED_MAGSYSTEMS, name="magsystems", validate_strings=True)
allowed_bandpasses = sa.Enum(*ALLOWED_BANDPASSES, name="bandpasses", validate_strings=True)
thumbnail_types = sa.Enum(*THUMBNAIL_TYPES, name='thumbnail_types', validate_strings=True)

py_allowed_magsystems = Enum('magsystems', ALLOWED_MAGSYSTEMS)
py_allowed_bandpasses = Enum('bandpasses', ALLOWED_BANDPASSES)
py_thumbnail_types = Enum('thumbnail_types', THUMBNAIL_TYPES)
