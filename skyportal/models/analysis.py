__all__ = ['AnalysisService']

import json

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy_utils.types import JSONType
from sqlalchemy.dialects.postgresql import ARRAY

from sqlalchemy_utils import URLType, EmailType
from sqlalchemy_utils.types.encrypted.encrypted_type import (
    StringEncryptedType,
    AesEngine,
)

from baselayer.app.models import Base
from baselayer.app.env import load_env

from ..enum_types import (
    allowed_analysis_types,
    allowed_analysis_input_types,
    allowed_external_authentication_types,
    ANALYSIS_TYPES,
    AUTHENTICATION_TYPES,
)

from .group import accessible_by_groups_members

_, cfg = load_env()


class AnalysisService(Base):
    __tablename__ = 'analysis_services'

    read = create = update = delete = accessible_by_groups_members

    name = sa.Column(
        sa.String,
        unique=True,
        index=True,
        nullable=False,
        doc='Unique name/identifier of the analysis service.',
    )

    display_name = sa.Column(
        sa.String, nullable=False, doc='Display name of the analysis service.'
    )

    description = sa.Column(
        sa.String,
        nullable=True,
        doc=(
            'Long-form description of what the analysis service does,'
            ' what it returns, and what it requires. Could include'
            ' links to documentation and code here.'
        ),
    )

    version = sa.Column(
        sa.String,
        nullable=True,
        doc='Semantic version (or githash) of the analysis service.',
    )

    contact_name = sa.Column(
        sa.String,
        nullable=True,
        doc=(
            'Name of person responsible for the service (ie. the maintainer). '
            ' This person does not need to be part of this SkyPortal instance.'
        ),
    )

    contact_email = sa.Column(
        EmailType(),
        nullable=True,
        doc='Email address of the person responsible for the service.',
    )

    url = sa.Column(
        URLType,
        nullable=False,
        doc=(
            "URL to running service accessible to this SkyPortal instance. "
            " For example, http://localhost:5000/analysis/<service_name>."
        ),
    )

    authentication_type = sa.Column(
        allowed_external_authentication_types,
        nullable=False,
        doc=(
            f'''Service authentiction method. One of: {', '.join(f"'{t}'" for t in AUTHENTICATION_TYPES)}.'''
            ' See https://docs.python-requests.org/en/master/user/authentication/'
        ),
    )

    _authinfo = sa.Column(
        StringEncryptedType(JSONType, cfg['app.secret_key'], AesEngine, 'pkcs5'),
        nullable=True,
        doc=('Contains authentication credentials for the service.'),
    )

    enabled = sa.Column(sa.Boolean, nullable=False, default=True)

    analysis_type = sa.Column(
        allowed_analysis_types,
        nullable=False,
        doc=f'''Type of analysis. One of: {', '.join(f"'{t}'" for t in ANALYSIS_TYPES)}''',
    )

    input_data_types = sa.Column(
        ARRAY(allowed_analysis_input_types),
        default=[],
        doc=(
            'List of allowed_analysis_input_types required by the service.'
            ' This data will be assembled and sent over to the analysis service.'
        ),
    )

    groups = relationship(
        "Group",
        secondary="group_analysisservices",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Groups that can access to this analysis service.",
    )

    timeout = sa.Column(
        sa.Float,
        default=3600.0,
        doc="Max time in seconds to wait for the analysis service to complete.",
    )

    upload_only = sa.Column(
        sa.Boolean,
        default=False,
        doc=(
            "If true, the analysis service is an upload type, where the user is responsible"
            " for providing the input data to the service. If false, the service is "
            " called using the data provided in input_data_types"
        ),
    )

    @property
    def authinfo(self):
        if self._authinfo is None:
            return {}
        else:
            return json.loads(self._authinfo)

    @authinfo.setter
    def authinfo(self, value):
        self._authinfo = value
