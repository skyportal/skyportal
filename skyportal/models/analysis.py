__all__ = ['AnalysisService', 'ObjAnalysis']

import json

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy_utils.types import JSONType, JSONB
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import ARRAY

from sqlalchemy_utils import URLType, EmailType
from sqlalchemy_utils.types.encrypted.encrypted_type import (
    StringEncryptedType,
    AesEngine,
)

from baselayer.app.models import (
    Base,
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
)
from baselayer.app.env import load_env

from ..enum_types import (
    allowed_analysis_types,
    allowed_analysis_input_types,
    allowed_external_authentication_types,
    ANALYSIS_TYPES,
    AUTHENTICATION_TYPES,
)


from .webhook import WebhookMixin
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


class AnalysisMixin:

    results = sa.Column(
        JSONB, default=None, nullable=False, doc="Searchable results in JSON format"
    )

    show_parameters = sa.Column(
        sa.Boolean,
        default=False,
        nullable=False,
        doc="Whether to render the parameters of this analysis",
    )

    show_plots = sa.Column(
        sa.Boolean,
        default=False,
        nullable=False,
        doc="Whether to render the plots of this analysis",
    )

    show_corner = sa.Column(
        sa.Boolean,
        default=False,
        nullable=False,
        doc="Whether to render the corner plots of this analysis",
    )

    @classmethod
    def backref_name(cls):
        if cls.__name__ == 'ObjAnalysis':
            return "obj_analyses"

    @declared_attr
    def analysis_service(cls):
        return relationship(
            AnalysisService,
            backref=cls.backref_name(),
            cascade="save-update, merge, refresh-expire, expunge",
            passive_deletes=True,
            doc="Analysis service this analysis uses.",
        )

    @declared_attr
    def creator(cls):
        return relationship(
            "User",
            back_populates=cls.backref_name(),
            doc="Analysis's creator.",
            uselist=False,
            foreign_keys=f"{cls.__name__}.creator_id",
        )

    @declared_attr
    def creator_id(cls):
        return sa.Column(
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the Analysis author's User instance.",
        )

    @declared_attr
    def groups(cls):
        return relationship(
            "Group",
            secondary="group_" + cls.backref_name(),
            cascade="save-update, merge, refresh-expire, expunge",
            passive_deletes=True,
            doc="Groups that can see the analysis.",
        )

    def construct_creator_info_dict(self):
        return {
            field: getattr(self.author, field)
            for field in ('username', 'first_name', 'last_name', 'gravatar_url')
        }


class ObjAnalysis(Base, AnalysisMixin, WebhookMixin):
    """Analysis on an Obj with a set of results as JSON"""

    __tablename__ = 'obj_analyses'

    create = AccessibleIfRelatedRowsAreAccessible(obj='read')
    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        obj='read'
    )
    update = delete = AccessibleIfUserMatches('creator')

    @declared_attr
    def obj_id(cls):
        return sa.Column(
            sa.ForeignKey('objs.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the ObjAnalysis's Obj.",
        )

    @declared_attr
    def obj(cls):
        return relationship(
            'Obj',
            back_populates=cls.backref_name(),
            doc="The ObjAnalysis's Obj.",
        )
