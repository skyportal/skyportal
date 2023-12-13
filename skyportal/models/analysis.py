__all__ = ['AnalysisService', 'ObjAnalysis', 'DefaultAnalysis']

import base64
from datetime import datetime, timedelta
import io
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

import joblib
import numpy as np
import matplotlib.pyplot as plt
import corner
import arviz
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy import event, inspect, or_, cast, func
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy_utils.types import JSONType
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.hybrid import hybrid_property

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
from baselayer.log import make_log

from skyportal.models import DBSession

from ..enum_types import (
    allowed_analysis_types,
    allowed_analysis_input_types,
    allowed_external_authentication_types,
    ANALYSIS_TYPES,
    AUTHENTICATION_TYPES,
)

from .webhook import WebhookMixin
from .group import accessible_by_groups_members
from .classification import Classification
from .group import Group

_, cfg = load_env()

log = make_log('models/analysis')

RE_SLASHES = re.compile(r'^[\w_\-\+\/\\]*$')
RE_NO_SLASHES = re.compile(r'^[\w_\-\+]*$')
MAX_FILEPATH_LENGTH = 255


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

    optional_analysis_parameters = sa.Column(
        JSONType,
        nullable=True,
        default=dict,
        doc=(
            'Optional parameters to be passed to the analysis service, along with '
            'possible values to be shown in the UI. '
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

    display_on_resource_dropdown = sa.Column(
        sa.Boolean,
        default=True,
        doc=(
            "If true, this analysis service will be displayed as a possible option"
            " for an end-user to run on a resource page (e.g. a source)."
            " If false, then the analysis will still be available programmatically,"
            " but will not be displayed as an option to end-users. Default: True."
        ),
    )

    is_summary = sa.Column(
        sa.Boolean,
        default=False,
        doc=(
            "If true, the results of an analysis using this service will be saved"
            " as a summary on the resource page (e.g. a source)."
            " This is useful for AI generated summaries of a source that should be displayed"
            " differently than the full results of an analysis. Default: False."
        ),
    )

    obj_analyses = relationship(
        'ObjAnalysis',
        back_populates='analysis_service',
        cascade='save-update, merge, refresh-expire, expunge, delete-orphan, delete',
        passive_deletes=True,
        doc="Instances of analysis applied to specific objects",
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

    # add the relationship to the DefaultAnalysis table
    default_analyses = relationship(
        'DefaultAnalysis',
        back_populates='analysis_service',
        cascade='save-update, merge, refresh-expire, expunge, delete-orphan, delete',
        passive_deletes=True,
        doc="Instances of analysis applied to specific objects",
    )


class DictNumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


class AnalysisMixin:
    def calc_hash(self):
        self.hash = joblib.hash(self.filename)

    @hybrid_property
    def has_inference_data(self):
        return self.data.get('inference_data', None) is not None

    @hybrid_property
    def has_plot_data(self):
        return self.data.get('plots', None) is not None

    @hybrid_property
    def number_of_analysis_plots(self):
        if not self.has_plot_data:
            return 0
        else:
            return len(self.data.get('plots', []))

    @hybrid_property
    def has_results_data(self):
        return self.data.get('results', None) is not None

    def serialize_results_data(self):
        """
        return the results data as a dictonary, even if it
        contains some numpy arrays
        """
        if not self.has_results_data:
            return {}
        results = self.data.get('results', {"format": "json", "data": {}})
        if not isinstance(results, dict):
            return {}

        if results.get('format', None) == "json":
            return results.get('data', {})
        elif results.get('format', None) == "joblib":
            try:
                buf = io.BytesIO()
                buf.write(base64.b64decode(results.get('data', None)))
                buf.seek(0)
                data = joblib.load(buf)
                jsons = json.dumps(data, cls=DictNumpyEncoder)
            except Exception as e:
                log(f"Error serializing results data: {e}")
                jsons = "{}"
            return json.loads(jsons)
        else:
            return {}

    def get_analysis_plot(self, plot_number=0):
        if not self.has_plot_data:
            return None

        if plot_number < 0 or plot_number >= self.number_of_analysis_plots:
            return None

        plot = self.data.get('plots')[plot_number]
        try:
            format = plot["format"]
        except Exception as e:
            format = "png"
            log(f"Warning: missing format in plot, assuming png {e}")

        buf = io.BytesIO()
        buf.write(base64.b64decode(plot['data']))
        buf.seek(0)

        return {"plot_data": buf, "plot_type": format}

    def generate_corner_plot(self, **plot_kwargs):
        """Generate a corner plot of the posterior from the inference data."""

        if not self.has_inference_data:
            return None

        # we could add different formats here in the future
        # but for now we only support netcdf4 formats
        if self.data['inference_data']["format"] not in ["netcdf4"]:
            raise ValueError('Inference data format not allowed.')

        f = tempfile.NamedTemporaryFile(
            suffix=".nc", prefix="inferencedata_", delete=False
        )
        f.close()
        f_handle = open(f.name, 'wb')
        f_handle.write(base64.b64decode(self.data['inference_data']['data']))
        f_handle.close()
        # N.B.: arviz/xarray memory maps the file, so we need to
        # remove the file only after using the data to make the plot
        inference_data = arviz.from_netcdf(f.name)

        try:
            # remove parameters with zero range in the data
            # which can happen with fixed parameters
            temp_range = [
                [
                    inference_data["posterior"][x].data.min(),
                    inference_data["posterior"][x].data.max(),
                    x,
                ]
                for x in inference_data["posterior"]
            ]
            for x in temp_range:
                # the min and max of this variable is the same:
                # probably a fixed parameter. Remove it (x[2]) from plotting
                # because it causes grief for corner
                if x[0] == x[1]:
                    del inference_data["posterior"][x[2]]

            fig = corner.corner(
                inference_data["posterior"],
                quantiles=[0.16, 0.5, 0.84],
                fig_kwargs=plot_kwargs,
            )
        except Exception as e:
            log(f"Failed to generate corner plot: {e}")
            return None
        finally:
            # now that we have the data in figure we can
            # remove this file
            os.remove(f.name)

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)

        return buf

    def load_data(self):
        """
        Load the associated analysis data from disk.
        """
        if self._full_name and os.path.exists(self._full_name):
            self._data = joblib.load(self._full_name)
        else:
            self._data = {}

    def save_data(self):
        """
        Save the associated analysis data to disk.
        """

        # there's a default value but it is best to provide a full path in the config
        root_folder = cfg.get('analysis_services.analysis_folder', 'analysis_data')

        # the filename can have alphanumeric, underscores, + or -
        self.check_path_string(self._unique_id)

        # make sure to replace windows style slashes
        subfolder = self._unique_id.replace("\\", "/")

        filename = f'analysis_{self.id}.joblib'

        path = os.path.join(root_folder, subfolder)
        if not os.path.exists(path):
            os.makedirs(path)

        full_name = os.path.join(path, filename)

        if len(full_name) > MAX_FILEPATH_LENGTH:
            raise ValueError(
                f'Full path to file {full_name} is longer than {MAX_FILEPATH_LENGTH} characters.'
            )

        joblib.dump(self._data, full_name, compress=3)
        self.filename = full_name

        # persist the filename
        self._full_name = full_name
        self.calc_hash()

    def delete_data(self):
        """
        Delete the associated data from disk
        """
        if self._full_name:
            if os.path.exists(self._full_name):
                os.remove(self._full_name)
            parent_dir = Path(self._full_name).parent
            try:
                if parent_dir.is_dir():
                    parent_dir.rmdir()
            except OSError:
                pass

        # reset the filename
        self._full_name = None

    @staticmethod
    def check_path_string(string, allow_slashes=False):
        if allow_slashes:
            reg = RE_SLASHES
        else:
            reg = RE_NO_SLASHES

        if string is None:
            raise ValueError("String cannot be None.")
        if not reg.match(string):
            raise ValueError(f'Illegal characters in string "{string}".')

    @hybrid_property
    def data(self):
        """Lazy load the data dictionary"""
        if not hasattr(self, "_data") or self._data is None:
            self.load_data()
        return self._data

    _unique_id = sa.Column(
        sa.String,
        nullable=False,
        unique=True,
        default=lambda: str(uuid.uuid4()),
        doc='Unique identifier for this analysis result.',
    )

    hash = sa.Column(
        sa.String,
        nullable=True,
        unique=False,
        doc='MD5sum hash of the data to be saved to file. Helps identify duplicate results.',
    )

    _full_name = sa.Column(
        sa.String,
        nullable=True,
        doc='full name of the file path where the data is saved.',
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

    analysis_parameters = sa.Column(
        JSONType,
        nullable=True,
        doc=('Optional parameters that are passed to the analysis service'),
    )

    input_filters = sa.Column(
        JSONType,
        nullable=True,
        doc=(
            'Optional filters that are applied to the input data that is passed to the analysis service'
        ),
    )

    @classmethod
    def backref_name(cls):
        if cls.__name__ == 'ObjAnalysis':
            return "obj_analyses"

    @declared_attr
    def author_id(cls):
        return sa.Column(
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the Annotation author's User instance.",
        )

    @declared_attr
    def author(cls):
        return relationship(
            "User",
            doc="Annotation's author.",
        )

    @declared_attr
    def analysis_service_id(cls):
        return sa.Column(
            sa.ForeignKey('analysis_services.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the associated analysis service.",
        )

    @declared_attr
    def analysis_service(cls):
        return relationship(
            "AnalysisService",
            back_populates=cls.backref_name(),
            doc="Analysis Service associated with this analysis.",
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


class ObjAnalysis(Base, AnalysisMixin, WebhookMixin):
    """Analysis on an Obj with a set of results as JSON"""

    __tablename__ = 'obj_analyses'

    create = AccessibleIfRelatedRowsAreAccessible(obj='read')
    read = accessible_by_groups_members & AccessibleIfRelatedRowsAreAccessible(
        obj='read'
    )
    update = delete = AccessibleIfUserMatches('author')

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


class DefaultAnalysis(Base):

    # this is a table that stores a default analysis for a given analysis service
    # this default analysis will be triggered based on a set of criteria
    # the criteria will be defined here as well, in a JSONB column called source_filter

    __tablename__ = 'default_analyses'

    create = read = update = delete = accessible_by_groups_members

    analysis_service_id = sa.Column(
        sa.ForeignKey('analysis_services.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the associated analysis service.",
    )

    analysis_service = relationship(
        "AnalysisService",
        back_populates="default_analyses",
        doc="Analysis Service associated with this analysis.",
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

    default_analysis_parameters = sa.Column(
        JSONType,
        nullable=True,
        doc=('Optional parameters that are passed to the analysis service'),
    )

    source_filter = sa.Column(
        psql.JSONB,
        nullable=False,
        doc="""
            JSONB column that defines the criteria for which this default analysis will be triggered.
            Example: {"classifications": {"name": "Kilonova", "probability": 0.9}}
        """,
    )

    stats = sa.Column(
        psql.JSONB,
        nullable=False,
        default={},
        doc="JSONB column that stores the stats for this default analysis",
    )

    groups = relationship(
        "Group",
        secondary="group_default_analyses",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Groups that can edit the default analysis, and see the analyses created by it.",
    )

    @declared_attr
    def author_id(cls):
        return sa.Column(
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
            doc="ID of the Annotation author's User instance.",
        )

    @declared_attr
    def author(cls):
        return relationship(
            "User",
            doc="Annotation's author.",
        )


@event.listens_for(ObjAnalysis, 'after_delete')
def delete_analysis_data_from_disk(mapper, connection, target):
    log(f'Deleting analysis data for analysis id={target.id}')
    target.delete_data()


@event.listens_for(AnalysisService, 'before_delete')
def delete_assoc_analysis_data_from_disk(mapper, connection, target):
    log(f'Deleting associated analysis data for analysis_service={target.id}')
    for analysis in target.obj_analyses:
        log(f' ... deleting analysis data for analysis id={analysis.id}')
        analysis.delete_data()


@event.listens_for(Classification, 'after_insert')
def create_default_analysis(mapper, connection, target):
    log(f'Checking for default analyses for classification {target.id}')

    @event.listens_for(inspect(target).session, "after_flush", once=True)
    def receive_after_flush(session, context):
        try:
            from skyportal.handlers.api.analysis import post_analysis

            target_data = target.to_dict()

            stmt = sa.select(DefaultAnalysis).where(
                DefaultAnalysis.source_filter['classifications'].contains(
                    [{"name": target_data['classification']}]
                ),
                or_(
                    func.coalesce(
                        DefaultAnalysis.stats['daily_count'].astext.cast(sa.Integer), 0
                    )
                    < func.coalesce(
                        DefaultAnalysis.stats['daily_limit'].astext.cast(sa.Integer), 10
                    ),
                    DefaultAnalysis.stats['last_run'].astext.cast(sa.DateTime)
                    < cast(datetime.utcnow() - timedelta(days=1), sa.DateTime),
                ),
                # make sure that the default analysis is associated with a group that the classification is associated with
                DefaultAnalysis.groups.any(
                    Group.id.in_([g.id for g in target_data["groups"]])
                ),
            )

            default_analyses = session.scalars(stmt).all()

            for default_analysis in default_analyses:
                classification_filter = next(
                    (
                        classification
                        for classification in default_analysis.source_filter[
                            "classifications"
                        ]
                        if classification["name"] == target_data['classification']
                    ),
                    None,
                )
                if classification_filter['probability'] <= target_data['probability']:
                    log(
                        f'Creating default analysis {default_analysis.analysis_service.name} for classification {target.id}'
                    )

                    with DBSession() as db_session:

                        try:
                            default_analysis = db_session.scalars(
                                DefaultAnalysis.select(
                                    default_analysis.author, mode="update"
                                ).where(DefaultAnalysis.id == default_analysis.id)
                            ).first()

                            if not {'daily_limit', 'daily_count', 'last_run'}.issubset(
                                default_analysis.stats.keys()
                            ):
                                default_analysis.stats = {
                                    'daily_limit': 10,
                                    'daily_count': 1,
                                    'last_run': datetime.utcnow().strftime(
                                        "%Y-%m-%dT%H:%M:%S.%f"
                                    ),
                                }
                            if datetime.strptime(
                                default_analysis.stats['last_run'],
                                "%Y-%m-%dT%H:%M:%S.%f",
                            ) < datetime.utcnow() - timedelta(days=1):
                                default_analysis.stats = {
                                    'daily_limit': default_analysis.stats[
                                        'daily_limit'
                                    ],
                                    'daily_count': 0,
                                    'last_run': datetime.utcnow().strftime(
                                        "%Y-%m-%dT%H:%M:%S.%f"
                                    ),
                                }
                            default_analysis.stats = {
                                'daily_limit': default_analysis.stats['daily_limit'],
                                'daily_count': default_analysis.stats['daily_count']
                                + 1,
                                'last_run': datetime.utcnow().strftime(
                                    "%Y-%m-%dT%H:%M:%S.%f"
                                ),
                            }
                            db_session.add(default_analysis)

                            post_analysis(
                                "obj",
                                target.obj_id,
                                current_user=default_analysis.author,
                                author=default_analysis.author,
                                groups=default_analysis.groups,
                                analysis_service=default_analysis.analysis_service,
                                analysis_parameters=default_analysis.default_analysis_parameters,
                                show_parameters=default_analysis.show_parameters,
                                show_plots=default_analysis.show_plots,
                                show_corner=default_analysis.show_corner,
                                notification=f"Default analysis {default_analysis.analysis_service.name} triggered by classification {target_data['classification']}",
                                session=db_session,
                            )
                        except Exception as e:
                            log(
                                f'Error creating default analysis with id {default_analysis.id}: {e}'
                            )
                            db_session.rollback()
        except Exception as e:
            log(f'Error creating default analyses on classification {target.id}: {e}')
