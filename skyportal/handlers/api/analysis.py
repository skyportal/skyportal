import copy
import io
import json
from urllib.parse import urlparse, urljoin
import datetime
import functools
import yaml

import os
import numpy as np
import pandas as pd
import requests
from requests_oauthlib import OAuth1
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from tornado.ioloop import IOLoop
from marshmallow.exceptions import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager

from baselayer.app.flow import Flow
from baselayer.app.access import auth_or_token, permissions
from baselayer.app.model_util import recursive_to_dict

from baselayer.log import make_log
from baselayer.app.env import load_env
from ...app_utils import get_app_base_url

from ...enum_types import (
    ANALYSIS_INPUT_TYPES,
    AUTHENTICATION_TYPES,
    ANALYSIS_TYPES,
    DEFAULT_ANALYSIS_FILTER_TYPES,
)

from ..base import BaseHandler

from ...models import (
    AnalysisService,
    Group,
    Photometry,
    Spectrum,
    Annotation,
    Classification,
    Obj,
    User,
    Comment,
    ObjAnalysis,
    DefaultAnalysis,
    UserNotification,
)
from .photometry import serialize

log = make_log('app/analysis')

_, cfg = load_env()

DEFAULT_ANALYSES_DAILY_LIMIT = 100

# check for API key
summary_config = copy.deepcopy(cfg['analysis_services.openai_analysis_service.summary'])
if summary_config.get("api_key"):
    # there may be a global API key set in the config file
    openai_api_key = summary_config.pop("api_key")
elif os.path.exists(".secret"):
    # try to get this key from the dev environment, useful for debugging
    openai_api_key = yaml.safe_load(open(".secret")).get("OPENAI_API_KEY")
else:
    openai_api_key = None


def valid_url(trial_url):
    """
    determine if the URL is valid
    """
    try:
        rez = urlparse(trial_url)
        return all([rez.scheme, rez.netloc])
    except ValueError:
        return False


def call_external_analysis_service(
    url,
    callback_url,
    inputs={},
    analysis_parameters={},
    authentication_type='none',
    authinfo=None,
    callback_method="POST",
    invalid_after=None,
    analysis_resource_type=None,
    resource_id=None,
    request_timeout=30.0,
):
    """
    Call an external analysis service with pre-assembled input data and user-specified
    authentication.

    The expectation is that any errors raised herein will be handled by the caller.
    """
    headers = {}
    auth = None
    payload_data = {
        "callback_url": callback_url,
        "inputs": inputs,
        "callback_method": callback_method,
        "invalid_after": str(invalid_after),
        "analysis_resource_type": analysis_resource_type,
        "resource_id": resource_id,
        "analysis_parameters": analysis_parameters,
    }

    if authentication_type == 'api_key':
        payload_data.update({authinfo['api_key_name']: authinfo['api_key']})
    elif authentication_type == 'header_token':
        headers.update(authinfo['header_token'])
    elif authentication_type == 'HTTPBasicAuth':
        auth = HTTPBasicAuth(authinfo['username'], authinfo['password'])
    elif authentication_type == 'HTTPDigestAuth':
        auth = HTTPDigestAuth(authinfo['username'], authinfo['password'])
    elif authentication_type == 'OAuth1':
        auth = OAuth1(
            authinfo['app_key'],
            authinfo['app_secret'],
            authinfo['user_oauth_token'],
            authinfo['user_oauth_token_secret'],
        )
    elif authentication_type == 'none':
        pass
    else:
        raise ValueError(f"Invalid authentication_type: {authentication_type}")

    try:
        result = requests.post(
            url,
            json=payload_data,
            headers=headers,
            auth=auth,
            timeout=request_timeout,
        )
    except requests.exceptions.Timeout:
        raise ValueError(f"Request to {url} timed out.")
    except Exception as e:
        raise Exception(f"Request to {url} had exception {e}.")

    return result


def generic_serialize(row, columns):
    return {
        c: getattr(row, c).tolist()
        if isinstance(getattr(row, c), np.ndarray)
        else getattr(row, c)
        for c in columns
    }


def get_associated_obj_resource(associated_resource_type):
    """
    What are the columns that we can allow to send to the external service
    should not be sending internal keys
    """
    associated_resource_type = associated_resource_type.lower()
    associated_resource_types = {
        "photometry": {
            "class": Photometry,
            "allowed_export_columns": [
                "mjd",
                "flux",
                "fluxerr",
                "mag",
                "magerr",
                "filter",
                "magsys",
                "zp",
                "instrument_name",
            ],
            "id_attr": 'obj_id',
        },
        "spectra": {
            "class": Spectrum,
            "allowed_export_columns": [
                "observed_at",
                "wavelengths",
                "fluxes",
                "errors",
                "units",
                "altdata",
                "created_at",
                "origin",
                "modified",
                "type",
            ],
            "id_attr": 'obj_id',
        },
        "annotations": {
            "class": Annotation,
            "allowed_export_columns": ["data", "modified", "origin", "created_at"],
            "id_attr": 'obj_id',
        },
        "comments": {
            "class": Comment,
            "allowed_export_columns": [
                "text",
                "bot",
                "modified",
                "origin",
                "created_at",
            ],
            "id_attr": 'obj_id',
        },
        "classifications": {
            "class": Classification,
            "allowed_export_columns": [
                "classification",
                "probability",
                "modified",
                "created_at",
            ],
            "id_attr": 'obj_id',
        },
        "redshift": {
            "class": Obj,
            "allowed_export_columns": [
                "redshift",
                "redshift_error",
                "redshift_origin",
            ],
            "id_attr": 'id',
        },
    }
    if associated_resource_type not in associated_resource_types:
        raise ValueError(
            f"Invalid associated_resource_type: {associated_resource_type}"
        )
    return associated_resource_types[associated_resource_type]


def post_analysis(
    analysis_resource_type,
    resource_id,
    current_user,
    author,
    groups,
    analysis_service,
    session,
    notification=None,
    analysis_parameters=None,
    show_parameters=False,
    show_plots=False,
    show_corner=False,
    input_filters=None,
):
    """
    Post an analysis to the database.

    Parameters
    ----------
    analysis_resource_type: str
        The type of resource we are analyzing.
    resource_id: str
        The ID of the resource we are analyzing.
    current_user: baselayer.app.models.User
        The user who is requesting the analysis.
    author: baselayer.app.models.User
        The user who will be the author of the analysis.
    groups: list of baselayer.app.models.Group
        The groups that will be able to view the analysis.
    analysis_service: skyportal.models.AnalysisService
        The analysis service to use.
    session: sqlalchemy.orm.session.Session
        The database session.
    analysis_parameters: dict
        The parameters to pass to the analysis service.
    show_parameters: bool
        Whether to show the parameters in the analysis.
    show_plots: bool
        Whether to show the plots in the analysis.
    show_corner: bool
        Whether to show the corner plot in the analysis.
    input_filters: list of str
        The filters to apply on the input data before sending it to the analysis service.

    Returns
    -------
    analysis_id: int
        The ID of the analysis.
    """

    input_data_types = analysis_service.input_data_types.copy()

    inputs = {"analysis_parameters": analysis_parameters.copy()}

    # if any analysis_parameters is a file, we discard it and just keep its name (if possible)
    keys_to_delete = []
    for k, v in analysis_parameters.items():
        if isinstance(v, str):
            if 'data:' in v and ';name=' in v:
                keys_to_delete.append(k)
    for k in keys_to_delete:
        try:
            analysis_parameters[k] = (
                analysis_parameters[k].split(';name=')[1].split(';')[0]
            )
        except Exception:
            del analysis_parameters[k]

    if analysis_resource_type.lower() == 'obj':
        obj_id = resource_id
        stmt = Obj.select(current_user).where(Obj.id == obj_id)
        obj = session.scalars(stmt).first()
        if obj is None:
            raise ValueError(f'Obj {obj_id} not found')

        # make sure the user has not exceeded the maximum number of analyses
        # for this object. This will help save space on the disk
        # an enforce a reasonable limit on the number of analyses.
        stmt = ObjAnalysis.select(current_user).where(ObjAnalysis.obj_id == obj_id)
        stmt = stmt.where(ObjAnalysis.author == author)
        stmt = stmt.where(ObjAnalysis.status == "completed")

        total_matches = session.execute(select(func.count()).select_from(stmt)).scalar()

        if total_matches >= cfg["analysis_services.max_analysis_per_obj_per_user"]:
            raise Exception(
                """'You have reached the maximum number of analyses for this object.'
                  ' Please delete some analyses before attempting to start more analyses.'
                  """
            )

        # Let's assemble the input data for this Obj
        for input_type in input_data_types:
            associated_resource = get_associated_obj_resource(input_type)
            stmt = (
                associated_resource['class']
                .select(current_user)
                .where(
                    getattr(
                        associated_resource['class'],
                        associated_resource['id_attr'],
                    )
                    == obj_id
                )
            )
            input_data = session.scalars(stmt).all()
            if input_type == 'photometry':
                input_data = [serialize(phot, 'ab', 'both') for phot in input_data]
                df = pd.DataFrame(input_data)

                if (
                    input_filters is not None
                    and input_filters.get('photometry') is not None
                ):
                    if len(input_filters.get('photometry').get('filters', [])) > 0:
                        df = df[
                            df['filter'].isin(
                                input_filters.get('photometry')['filters']
                            )
                        ]
                    if len(input_filters.get('photometry').get('instruments', [])) > 0:
                        # we want to make sure that after this runs, the user can still figure out
                        # what instrument he filtered on, non trivial when only reporting the id used
                        # the instrument could be edited, deleted, ...
                        # so, we grab the name and inject that in the input_filters
                        df = df[
                            df['instrument_id'].isin(
                                input_filters.get('photometry')['instruments']
                            )
                        ]
                        instruments = df["instrument_name"].unique().tolist()
                        input_filters['photometry']['instruments_by_name'] = instruments

                df = df[associated_resource['allowed_export_columns']]
                # drop duplicate mjd/filter points, keeping first
                df = df.drop_duplicates(["mjd", "filter"]).reset_index(drop=True)
            else:
                input_data = [
                    generic_serialize(
                        row, associated_resource['allowed_export_columns']
                    )
                    for row in input_data
                ]
                df = pd.DataFrame(input_data)
            inputs[input_type] = df.to_csv(index=False)

        invalid_after = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=analysis_service.timeout
        )

        analysis = ObjAnalysis(
            obj=obj,
            author=author,
            groups=groups,
            analysis_service=analysis_service,
            show_parameters=show_parameters,
            show_plots=show_plots,
            show_corner=show_corner,
            analysis_parameters=analysis_parameters,
            status='queued',
            handled_by_url="api/webhook/obj_analysis",
            invalid_after=invalid_after,
            input_filters=input_filters,
        )
    # Add more analysis_resource_types here one day (eg. GCN)
    else:
        raise ValueError(f'analysis_resource_type must be one of {", ".join(["obj"])}')

    session.add(analysis)
    try:
        session.commit()
    except IntegrityError as e:
        raise Exception(f'Analysis already exists: {str(e)}')
    except Exception as e:
        raise Exception(f'Unexpected error creating analysis: {str(e)}')

    # Now call the analysis service to start the analysis, using the `input` data
    # that we assembled above.
    callback_url = urljoin(
        get_app_base_url(), f"{analysis.handled_by_url}/{analysis.token}"
    )
    external_analysis_service = functools.partial(
        call_external_analysis_service,
        analysis_service.url,
        callback_url,
        inputs=inputs,
        authentication_type=analysis_service.authentication_type,
        authinfo=analysis_service.authinfo,
        callback_method="POST",
        invalid_after=invalid_after,
        analysis_resource_type=analysis_resource_type,
        resource_id=resource_id,
    )

    flow = Flow()
    flow.push(
        current_user.id,
        action_type="baselayer/SHOW_NOTIFICATION",
        payload={
            "note": f'Sending data to analysis service {analysis_service.name} to start the analysis.'
            if notification is None
            else notification,
            "type": "info",
        },
    )

    if notification is not None and notification != "":
        try:
            user_notification = UserNotification(
                user=current_user,
                text=notification,
                notification_type="default_analysis",
                url=f"/source/{obj_id}/analysis/{analysis.id}",
            )
            session.add(user_notification)
            session.commit()
        except Exception as e:
            log(f"Could not add notification: {e}")

    def analysis_done_callback(
        future,
        logger=log,
        analysis_id=analysis.id,
        analysis_service_id=analysis_service.id,
        analysis_resource_type=analysis_resource_type,
    ):
        """
        Callback function for when the analysis service is done.
        Updates the Analysis object with the results/errors.
        """
        # grab the analysis (only Obj for now)
        if analysis_resource_type.lower() == 'obj':
            try:
                analysis = session.query(ObjAnalysis).get(analysis_id)
                if analysis is None:
                    logger.error(f'Analysis {analysis_id} not found')
                    return
            except Exception as e:
                log(f'Could not access Analysis {analysis_id} {e}.')
                return
        else:
            log(f"Invalid analysis_resource_type: {analysis_resource_type}")
            return

        analysis.last_activity = datetime.datetime.utcnow()
        try:
            result = future.result()
            analysis.status = 'pending' if result.status_code == 200 else 'failure'
            # truncate the return just so we dont have a huge string in the database
            analysis.status_message = result.text[:1024]
        except Exception:
            analysis.status = 'failure'
            analysis.status_message = str(future.exception())[:1024]
        finally:
            logger(
                f"[id={analysis_id} service={analysis_service_id}] status='{analysis.status}' message='{analysis.status_message}'"
            )
            session.commit()
            if analysis_resource_type.lower() == 'obj':
                try:
                    flow = Flow()
                    flow.push(
                        '*',
                        'skyportal/REFRESH_OBJ_ANALYSES',
                        payload={'obj_key': analysis.obj.internal_key},
                    )
                except Exception as e:
                    logger(f"Could not refresh analyses: {e}")
                    pass

    # Start the analysis service in a separate thread and log any exceptions
    x = IOLoop.current().run_in_executor(None, external_analysis_service)
    x.add_done_callback(analysis_done_callback)

    return analysis.id


class AnalysisServiceHandler(BaseHandler):
    """Handler for analysis services."""

    @permissions(["Manage Analysis Services"])
    def post(self):
        f"""
        ---
        description: POST a new Analysis Service.
        tags:
          - analysis_services
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                    description: Unique name/identifier of the analysis service.
                  display_name:
                    type: string
                    description: Display name of the analysis service.
                  description:
                    type: string
                    description: Description of the analysis service.
                  version:
                    type: string
                    description: Semantic version (or githash) of the analysis service.
                  contact_name:
                    type: string
                    description: |
                        Name of person responsible for the service (ie. the maintainer).
                        This person does not need to be part of this SkyPortal instance.
                  contact_email:
                    type: string
                    description: Email address of the person responsible for the service.
                  url:
                    type: string
                    description: |
                        URL to running service accessible to this SkyPortal instance.
                        For example, http://localhost:5000/analysis/<service_name>.
                  optional_analysis_parameters:
                    type: object
                    additionalProperties:
                      type: array
                      items:
                        type: string
                    description: |
                        Optional URL parameters that can be passed to the service, along
                        with a list of possible values (to be used in a dropdown UI)
                  authentication_type:
                    type: string
                    description: |
                        Service authentiction method. One of: {', '.join(f"'{t}'" for t in AUTHENTICATION_TYPES)}.
                        See https://docs.python-requests.org/en/master/user/authentication/
                  _authinfo:
                    type: object
                    description: |
                        Authentication secrets for the service. Not needed if authentication_type is "none".
                        This should be a string that can be parsed by the python json.loads() function and
                        should contain the key `authentication_type`. Values of this key will be used
                        to POST into the remote analysis service.
                  enabled:
                    type: boolean
                    description: Whether the service is enabled or not.
                  analysis_type:
                    type: string
                    description: Type of analysis. One of: {', '.join(f"'{t}'" for t in ANALYSIS_TYPES)}
                  input_data_types:
                    type: array
                    items:
                        type: string
                    description: |
                        List of input data types that the service requires. Zero to many of:
                        {', '.join(f"'{t}'" for t in ANALYSIS_INPUT_TYPES)}
                  timeout:
                    type: float
                    description: Max time in seconds to wait for the analysis service to complete. Default is 3600.0.
                    default: 3600.0
                  is_summary:
                    type: boolean
                    description: |
                        Establishes that analysis results on the resource should be considered a summary
                    default: false
                  display_on_resource_dropdown:
                    type: boolean
                    description: |
                        Show this analysis service on the analysis dropdown of the resource
                    default: true
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups should be
                      able to use the Analysis Service. Defaults to all of requesting
                      user's groups.
                required:
                  - name
                  - url
                  - authentication_type
                  - analysis_type
                  - input_data_types
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
                            id:
                              type: integer
                              description: New AnalysisService ID
        """
        data = self.get_json()

        if not data.get('url', None):
            return self.error('`url` is required to add an Analysis Service.')
        else:
            if not valid_url(data.get('url', None)):
                return self.error(
                    'a valid `url` is required to add an Analysis Service.'
                )
        try:
            _ = json.loads(data.get('optional_analysis_parameters', '{}'))
        except json.decoder.JSONDecodeError:
            return self.error(
                'Could not parse `optional_analysis_parameters` as JSON.', status=400
            )

        authentication_type = data.get('authentication_type', None)
        if not authentication_type:
            return self.error(
                '`authentication_type` is required to add an Analysis Service.'
            )

        if authentication_type not in AUTHENTICATION_TYPES:
            return self.error(
                f'`authentication_type` must be one of: {", ".join([t for t in AUTHENTICATION_TYPES])}.'
            )
        else:
            if authentication_type != 'none':
                _authinfo = data.get('_authinfo', None)
                if not _authinfo:
                    return self.error(
                        '`_authinfo` is required to add an Analysis Service '
                        ' when authentication_type is not "none".'
                    )
                try:
                    _authinfo = json.loads(_authinfo)
                except json.JSONDecodeError:
                    return self.error(
                        '`_authinfo` must be parseable to a valid JSON object.'
                    )
                if authentication_type not in _authinfo:
                    return self.error(
                        f'`_authinfo` must contain a key for "{authentication_type}".'
                    )

        group_ids = data.pop('group_ids', None)
        with self.Session() as session:
            if not group_ids:
                group_ids = [g.id for g in self.current_user.accessible_groups]

            groups = (
                session.scalars(
                    Group.select(self.current_user).where(Group.id.in_(group_ids))
                )
                .unique()
                .all()
            )
            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.',
                    status=403,
                )

            schema = AnalysisService.__schema__()
            try:
                analysis_service = schema.load(data)
            except ValidationError as e:
                return self.error(
                    "Invalid/missing parameters: " f"{e.normalized_messages()}"
                )

            session.add(analysis_service)
            analysis_service.groups = groups

            try:
                session.commit()
            except IntegrityError as e:
                return self.error(
                    f'Analysis Service with that name already exists: {str(e)}'
                )
            except Exception as e:
                return self.error(f'Unexpected Error adding Analysis Service: {str(e)}')

            self.push_all(action='skyportal/REFRESH_ANALYSIS_SERVICES')
            return self.success(data={"id": analysis_service.id})

    @auth_or_token
    def get(self, analysis_service_id=None):
        """
        ---
        single:
          description: Retrieve an Analysis Service by id
          tags:
            - analysis_services
          parameters:
            - in: path
              name: analysis_service_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleAnalysisService
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all Analysis Services
          tags:
            - analysis_services
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfAnalysisServices
            400:
              content:
                application/json:
                  schema: Error
        """
        with self.Session() as session:
            if analysis_service_id is not None:
                s = session.scalars(
                    AnalysisService.select(session.user_or_token).where(
                        AnalysisService.id == analysis_service_id
                    )
                ).first()
                if s is None:
                    return self.error(
                        'Cannot access this Analysis Service.', status=403
                    )

                analysis_dict = recursive_to_dict(s)
                analysis_dict["groups"] = s.groups
                return self.success(data=analysis_dict)

            # retrieve multiple services
            analysis_services = session.scalars(
                AnalysisService.select(session.user_or_token)
            ).all()

            ret_array = []
            for a in analysis_services:
                analysis_dict = recursive_to_dict(a)
                analysis_dict["groups"] = a.groups
                if isinstance(a.optional_analysis_parameters, str):
                    analysis_dict["optional_analysis_parameters"] = json.loads(
                        a.optional_analysis_parameters
                    )
                elif isinstance(a.optional_analysis_parameters, dict):
                    analysis_dict[
                        "optional_analysis_parameters"
                    ] = a.optional_analysis_parameters
                else:
                    return self.error(
                        message='optional_analysis_parameters must be dictionary or string'
                    )
                ret_array.append(analysis_dict)

            return self.success(data=ret_array)

    @permissions(["Manage Analysis Services"])
    def patch(self, analysis_service_id):
        f"""
        ---
        description: Update an Analysis Service.
        tags:
          - analysis_services
        parameters:
          - in: path
            name: analysis_service_id
            required: True
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                    description: Unique name/identifier of the analysis service.
                  display_name:
                    type: string
                    description: Display name of the analysis service.
                  description:
                    type: string
                    description: Description of the analysis service.
                  version:
                    type: string
                    description: Semantic version (or githash) of the analysis service.
                  contact_name:
                    type: string
                    description: |
                        Name of person responsible for the service (ie. the maintainer).
                        This person does not need to be part of this SkyPortal instance.
                  contact_email:
                    type: string
                    description: Email address of the person responsible for the service.
                  url:
                    type: string
                    description: |
                        URL to running service accessible to this SkyPortal instance.
                        For example, http://localhost:5000/analysis/<service_name>.
                  optional_analysis_parameters:
                    type: object
                    additionalProperties:
                      type: array
                      items:
                        type: string
                    description: |
                        Optional URL parameters that can be passed to the service, along
                        with a list of possible values (to be used in a dropdown UI)
                  authentication_type:
                    type: string
                    description: |
                        Service authentiction method. One of: {', '.join(f"'{t}'" for t in AUTHENTICATION_TYPES)}.
                        See https://docs.python-requests.org/en/master/user/authentication/
                  authinfo:
                    type: object
                    description: Authentication secrets for the service. Not needed if authentication_type is "none".
                  enabled:
                    type: boolean
                    description: Whether the service is enabled or not.
                  analysis_type:
                    type: string
                    description: Type of analysis. One of: {', '.join(f"'{t}'" for t in ANALYSIS_TYPES)}
                  input_data_types:
                    type: array
                    items:
                        type: string
                    description: |
                        List of input data types that the service requires. Zero to many of:
                        {', '.join(f"'{t}'" for t in ANALYSIS_INPUT_TYPES)}
                  timeout:
                    type: float
                    description: Max time in seconds to wait for the analysis service to complete. Default is 3600.0.
                    default: 3600.0
                  is_summary:
                    type: boolean
                    description: |
                        Establishes that analysis results on the resource should be considered a summary
                    default: false
                  display_on_resource_dropdown:
                    type: boolean
                    description: |
                        Show this analysis service on the analysis dropdown of the resource
                    default: true
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups should be
                      able to use the Analysis Service.
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        try:
            analysis_service_id = int(analysis_service_id)
        except ValueError:
            return self.error('analysis_service_id must be an int.')

        with self.Session() as session:
            s = session.scalars(
                AnalysisService.select(session.user_or_token, mode="update").where(
                    AnalysisService.id == analysis_service_id
                )
            ).first()
            if s is None:
                return self.error('Cannot access this Analysis Service.', status=403)

            data = self.get_json()
            group_ids = data.pop('group_ids', None)

            schema = AnalysisService.__schema__()
            try:
                new_analysis_service = schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )

            new_analysis_service.id = analysis_service_id
            session.merge(new_analysis_service)

            if group_ids is not None:
                groups = (
                    session.scalars(
                        Group.select(self.current_user).where(Group.id.in_(group_ids))
                    )
                    .unique()
                    .all()
                )
                if {g.id for g in groups} != set(group_ids):
                    return self.error(
                        f'Cannot find one or more groups with IDs: {group_ids}.'
                    )

                if not all(
                    [group in self.current_user.accessible_groups for group in groups]
                ):
                    return self.error(
                        "Cannot change groups for Analysis Services that you are not a member of."
                    )
                new_analysis_service.groups = groups

            session.commit()
            return self.success()

    @permissions(["Manage Analysis Services"])
    def delete(self, analysis_service_id):
        """
        ---
        description: Delete an Analysis Service.
        tags:
          - analysis_services
        parameters:
          - in: path
            name: analysis_service_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            analysis_service = session.scalars(
                AnalysisService.select(session.user_or_token, mode="delete").where(
                    AnalysisService.id == analysis_service_id
                )
            ).first()
            if analysis_service is None:
                return self.error('Cannot delete this Analysis Service.', status=403)
            session.delete(analysis_service)
            session.commit()

            self.push_all(action='skyportal/REFRESH_ANALYSIS_SERVICES')
            return self.success()


class AnalysisHandler(BaseHandler):
    @permissions(['Run Analyses'])
    async def post(self, analysis_resource_type, resource_id, analysis_service_id):
        """
        ---
        description: Begin an analysis run
        tags:
          - analysis
        parameters:
          - in: path
            name: analysis_resource_type
            required: true
            schema:
              type: string
            description: |
               What underlying data the analysis is on:
               must be "obj" (more to be added in the future)
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
            description: |
               The ID of the underlying data.
               This would be a string for an object ID.
          - in: path
            name: analysis_service_id
            required: true
            schema:
              type: string
            description: the analysis service id to be used
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  show_parameters:
                    type: boolean
                    description: Whether to render the parameters of this analysis
                  show_plots:
                    type: boolean
                    description: Whether to render the plots of this analysis
                  show_corner:
                    type: boolean
                    description: Whether to render the corner plots of this analysis
                  input_filters:
                    type: array
                    description: Filters to apply to the input data
                  analysis_parameters:
                    type: object
                    description: Dictionary of parameters to be passed thru to the analysis
                    additionalProperties:
                        type: string
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups should be
                      able to view analysis results. Defaults to all of requesting user's
                      groups.
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
                            analysis_id:
                              type: integer
                              description: New analysis ID
        """
        try:
            data = self.get_json()
        except Exception as e:
            return self.error(f'Error parsing JSON: {e}')

        with self.Session() as session:

            stmt = AnalysisService.select(self.current_user).where(
                AnalysisService.id == analysis_service_id
            )
            analysis_service = session.scalars(stmt).first()
            if analysis_service is None:
                return self.error(
                    message=f'Could not access Analysis Service ID: {analysis_service_id}.',
                    status=403,
                )

            if analysis_service.upload_only:
                return self.error(
                    message=(
                        f'Analysis Service ID: {analysis_service_id} is of type upload_only.'
                        ' Please use the analysis_upload endpoint.'
                    ),
                    status=403,
                )

            analysis_parameters = data.get('analysis_parameters', {})

            if isinstance(analysis_service.optional_analysis_parameters, str):
                optional_analysis_parameters = json.loads(
                    analysis_service.optional_analysis_parameters
                )
            else:
                optional_analysis_parameters = (
                    analysis_service.optional_analysis_parameters
                )

            if not set(analysis_parameters.keys()).issubset(
                set(optional_analysis_parameters.keys())
            ):
                return self.error(
                    f'Invalid analysis_parameters: {analysis_parameters}.', status=400
                )

            if analysis_service.is_summary:
                user_id = self.associated_user_object.id
                user = session.scalars(
                    User.select(session.user_or_token, mode="update").where(
                        User.id == user_id
                    )
                ).first()
                if user is None:
                    return self.error('Cannot find user.', status=400)

                if (
                    user.preferences.get("summary", {})
                    .get("OpenAI", {})
                    .get('active', False)
                ):
                    user_pref_openai = user.preferences["summary"]["OpenAI"].copy()
                    analysis_parameters["openai_api_key"] = user_pref_openai["apikey"]
                    user_pref_openai.pop("apikey", None)
                    user_pref_openai.pop("active", None)
                    analysis_parameters["summary_parameters"] = user_pref_openai
                elif openai_api_key is not None:
                    analysis_parameters["openai_api_key"] = openai_api_key
                    analysis_parameters["summary_parameters"] = summary_config

            group_ids = data.pop('group_ids', None)
            if not group_ids:
                group_ids = [g.id for g in self.current_user.accessible_groups]

            groups = session.scalars(
                Group.select(self.current_user).where(Group.id.in_(group_ids))
            ).all()
            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.'
                )

            author = self.associated_user_object
            input_filters = data.get('input_filters', {})
            if input_filters is not None:
                if (
                    "photometry" in analysis_service.input_data_types
                    and "photometry" in input_filters
                ):
                    filters = input_filters.get('photometry', {}).get('filters', [])
                    instruments = input_filters.get('photometry', {}).get(
                        'instruments', []
                    )
                    if filters is not None:
                        filters = [f.strip() for f in filters if f.strip() != ""]
                        if len(filters) > 0:
                            input_filters['photometry']['filters'] = filters
                    if instruments is not None:
                        instruments = [
                            int(i.strip()) for i in instruments if isinstance(i, str)
                        ]
                        if len(instruments) > 0:
                            input_filters['photometry']['instruments'] = instruments

            try:
                analysis_id = post_analysis(
                    analysis_resource_type,
                    resource_id,
                    self.current_user,
                    author,
                    groups,
                    analysis_service,
                    analysis_parameters=data.get('analysis_parameters', {}),
                    show_parameters=data.get('show_parameters', False),
                    show_plots=data.get('show_plots', False),
                    show_corner=data.get('show_corner', False),
                    input_filters=input_filters,
                    session=session,
                )
                return self.success(data={"id": analysis_id})
            except Exception as e:
                if 'not found' in str(e).lower():
                    return self.error(f'Error posting analysis: {e}', status=404)
                else:
                    return self.error(f'Error posting analysis: {e}')

    @auth_or_token
    def get(self, analysis_resource_type, analysis_id=None):
        """
        ---
        single:
          description: Retrieve an Analysis by id
          tags:
            - analysis
          parameters:
            - in: path
              name: analysis_resource_type
              required: true
              schema:
                type: string
              description: |
                What underlying data the analysis is on:
                must be "obj" (more to be added in the future)
            - in: path
              name: analysis_id
              required: false
              schema:
                type: int
              description: |
                ID of the analysis to return.
            - in: query
              name: objID
              nullable: true
              schema:
                type: string
              description: |
                Return any analysis on an object with ID objID
            - in: query
              name: analysisServiceID
              required: false
              schema:
                type: int
              description: |
                ID of the analysis service used to create the analysis, used only if no analysis_id is given
            - in: query
              name: includeAnalysisData
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include the data associated
                with the analysis in the response. Could be a large
                amount of data. Only works for single analysis requests.
                Defaults to false.
            - in: query
              name: summaryOnly
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to return only analyses that
                use analysis services with `is_summary` set to true.
                Defaults to false.
            - in: query
              name: includeFilename
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include the filename of the
                data associated with the analysis in the response. Defaults to false.
          responses:
            200:
              content:
                application/json:
                  schema: SingleObjAnalysis
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all Analyses
          tags:
            - analysis
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfObjAnalysiss
            400:
              content:
                application/json:
                  schema: Error
        """
        include_analysis_data = self.get_query_argument(
            "includeAnalysisData", False
        ) in ["True", "t", "true", "1", True, 1]
        include_filename = self.get_query_argument("includeFilename", False)
        summary_only = self.get_query_argument("summaryOnly", False)

        obj_id = self.get_query_argument('objID', None)
        analysis_service_id = self.get_query_argument('analysisServiceID', None)

        with self.Session() as session:
            if obj_id is not None:
                stmt = Obj.select(self.current_user).where(Obj.id == obj_id)
                obj = session.scalars(stmt).first()
                if obj is None:
                    return self.error(f'Obj {obj_id} not found', status=404)

            if analysis_resource_type.lower() == 'obj':
                if analysis_id is not None:
                    stmt = ObjAnalysis.select(self.current_user).where(
                        ObjAnalysis.id == analysis_id
                    )
                    if obj_id:
                        stmt = stmt.where(ObjAnalysis.obj_id.contains(obj_id.strip()))

                    analysis = session.scalars(stmt).first()
                    if analysis is None:
                        return self.error('Cannot access this Analysis.', status=403)

                    analysis_dict = recursive_to_dict(analysis)

                    # dont return the openai api key if its there
                    if "analysis_parameters" in analysis_dict:
                        analysis_dict["analysis_parameters"].pop("openai_api_key", None)

                    stmt = AnalysisService.select(self.current_user).where(
                        AnalysisService.id == analysis.analysis_service_id
                    )
                    analysis_service = session.scalars(stmt).first()
                    analysis_dict[
                        "analysis_service_name"
                    ] = analysis_service.display_name
                    analysis_dict[
                        "analysis_service_description"
                    ] = analysis_service.description
                    analysis_dict["num_plots"] = analysis.number_of_analysis_plots

                    if include_filename:
                        analysis_dict["filename"] = analysis._full_name
                    analysis_dict["groups"] = analysis.groups
                    if include_analysis_data:
                        analysis_dict["data"] = analysis.data

                    return self.success(data=analysis_dict)

                # retrieve multiple analyses
                stmt = ObjAnalysis.select(self.current_user)
                if obj_id:
                    stmt = stmt.where(ObjAnalysis.obj_id.contains(obj_id.strip()))
                if analysis_service_id:
                    stmt = stmt.where(
                        ObjAnalysis.analysis_service_id == analysis_service_id
                    )
                analyses = session.scalars(stmt).unique().all()

                ret_array = []
                analysis_services_dict = {}
                for a in analyses:
                    analysis_dict = recursive_to_dict(a)
                    if "analysis_parameters" in analysis_dict:
                        analysis_dict["analysis_parameters"].pop("openai_api_key", None)

                    if a.analysis_service_id not in analysis_services_dict.keys():
                        stmt = AnalysisService.select(self.current_user).where(
                            AnalysisService.id == a.analysis_service_id
                        )
                        analysis_service = session.scalars(stmt).first()
                        if analysis_service is not None:
                            analysis_services_dict.update(
                                {
                                    a.analysis_service_id: {
                                        "analysis_service_name": analysis_service.display_name,
                                        "analysis_service_description": analysis_service.description,
                                        "analysis_serivce_display_as_summary": analysis_service.is_summary,
                                    }
                                }
                            )

                    if a.analysis_service_id in analysis_services_dict.keys():
                        service_info = analysis_services_dict[a.analysis_service_id]
                        analysis_dict["analysis_service_name"] = service_info[
                            "analysis_service_name"
                        ]
                        analysis_dict["analysis_service_description"] = service_info[
                            "analysis_service_description"
                        ]

                    analysis_dict["groups"] = a.groups
                    if include_filename:
                        analysis_dict["filename"] = a._full_name
                    if (
                        summary_only
                        and not service_info["analysis_serivce_display_as_summary"]
                    ):
                        # the analysis service is not a summary service, so skip returning this analysis
                        continue
                    ret_array.append(analysis_dict)
            else:
                return self.error(
                    f'analysis_resource_type must be one of {", ".join(["obj"])}',
                    status=404,
                )
            return self.success(data=ret_array)

    @permissions(["Run Analyses"])
    def delete(self, analysis_resource_type, analysis_id):
        """
        ---
        description: Delete an Analysis.
        tags:
          - analysis
        parameters:
          - in: path
            name: analysis_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            if analysis_resource_type.lower() == 'obj':
                stmt = (
                    ObjAnalysis.select(self.current_user)
                    .join(ObjAnalysis.obj)
                    .join(ObjAnalysis.analysis_service)
                    .options(contains_eager(ObjAnalysis.analysis_service))
                    .options(contains_eager(ObjAnalysis.obj))
                    .where(ObjAnalysis.id == analysis_id)
                )
                analysis = session.scalars(stmt).first()
                if analysis is None:
                    return self.error('Cannot access this Analysis.', status=403)

                if analysis.obj.summary_history is not None:
                    analysis.obj.summary_history = [
                        x
                        for x in analysis.obj.summary_history
                        if x.get("analysis_id", -1) != analysis.id
                    ]
                session.delete(analysis)
                session.commit()

                try:
                    flow = Flow()
                    if analysis.analysis_service.is_summary:
                        flow.push(
                            '*',
                            'skyportal/REFRESH_SOURCE',
                            payload={'obj_key': analysis.obj.internal_key},
                        )
                    elif analysis_resource_type == 'obj':
                        flow.push(
                            '*',
                            'skyportal/REFRESH_OBJ_ANALYSES',
                            payload={'obj_key': analysis.obj.internal_key},
                        )
                except Exception as e:
                    log(f"Error pushing updates to source: {e}")

                return self.success()
            else:
                return self.error(
                    f'analysis_resource_type must be one of {", ".join(["obj"])}',
                    status=404,
                )


class AnalysisProductsHandler(BaseHandler):
    @auth_or_token
    async def get(
        self, analysis_resource_type, analysis_id, product_type, plot_number=0
    ):
        """
        ---
        description: Retrieve primary data associated with an Analysis.
        tags:
        - analysis
        parameters:
        - in: path
          name: analysis_resource_type
          required: true
          schema:
            type: string
          description: |
            What underlying data the analysis is on:
            must be "obj" (more to be added in the future)
        - in: path
          name: analysis_id
          required: true
          schema:
            type: integer
        - in: path
          name: product_type
          required: true
          schema:
            type: string
          description: |
            What type of data to retrieve:
            must be one of "corner", "results", or "plot"
        - in: path
          name: plot_number
          required: false
          schema:
            type: integer
          description: |
            if product_type == "plot", which
            plot number should be returned?
            Default to zero (first plot).
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  download:
                    type: bool
                    description: |
                        Download the results as a file
                  plot_kwargs:
                    type: object
                    additionalProperties:
                      type: object
                    description: |
                        Extra parameters to pass to the plotting functions
                        if new plots are to be generated (e.g. with corner plots)
        responses:
          200:
            description: Requested analysis file
            content:
              application/json:
                schema:
                  type: object
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            if analysis_resource_type.lower() == 'obj':
                if analysis_id is not None:
                    stmt = ObjAnalysis.select(self.current_user).where(
                        ObjAnalysis.id == analysis_id
                    )
                    analysis = session.scalars(stmt).first()
                    if analysis is None:
                        return self.error('Cannot access this Analysis.', status=403)

                    if analysis.data in [None, {}]:
                        return self.error(
                            "No data found for this Analysis.", status=404
                        )

                    if product_type.lower() == "corner":
                        if not analysis.has_inference_data:
                            return self.error(
                                "No inference data found for this Analysis.", status=404
                            )

                        plot_kwargs = self.get_query_argument("plot_kwargs", {})
                        filename = f"analysis_{analysis.obj_id}_corner.png"
                        output_type = "png"
                        output_data = analysis.generate_corner_plot(**plot_kwargs)
                        if output_data is not None:
                            await self.send_file(
                                output_data, filename, output_type=output_type
                            )
                            return
                    elif product_type.lower() == "results":
                        if not analysis.has_results_data:
                            return self.error(
                                "No results data found for this Analysis.", status=404
                            )

                        result = analysis.serialize_results_data()

                        if result:
                            download = self.get_query_argument("download", False)
                            if download:
                                filename = f"analysis_{analysis.obj_id}.json"
                                buf = io.BytesIO()
                                buf.write(json.dumps(result).encode('utf-8'))
                                buf.seek(0)

                                await self.send_file(buf, filename, output_type='json')
                                return
                            else:
                                return self.success(data=result)
                        else:
                            return self.error(
                                "No results data found for this Analysis.", status=404
                            )
                    elif product_type.lower() == "plots":
                        if not analysis.has_plot_data:
                            return self.error(
                                "No plot data found for this Analysis.", status=404
                            )
                        try:
                            plot_number = int(plot_number)
                        except Exception as e:
                            return self.error(
                                f"plot_number must be an integer. {e}", status=400
                            )
                        if (
                            plot_number < 0
                            or plot_number >= analysis.number_of_analysis_plots
                        ):
                            return self.error(
                                "Invalid plot number. "
                                f"There is/are {analysis.number_of_analysis_plots} plot(s) available for this analysis",
                                status=404,
                            )

                        result = analysis.get_analysis_plot(plot_number=plot_number)
                        if result is not None:
                            output_data = result["plot_data"]
                            output_type = result["plot_type"].lower()
                            filename = f"analysis_{analysis.obj_id}_plot_{plot_number}.{output_type}"
                            await self.send_file(
                                output_data, filename, output_type=output_type
                            )
                            return
                    else:
                        return self.error(
                            f"Invalid product type: {product_type}", status=404
                        )
            else:
                return self.error(
                    f'analysis_resource_type must be one of {", ".join(["obj"])}',
                    status=404,
                )

            return self.error("No data found for this Analysis.", status=404)


class AnalysisUploadOnlyHandler(BaseHandler):
    @permissions(['Run Analyses'])
    def post(self, analysis_resource_type, resource_id, analysis_service_id):
        """
        ---
        description: Upload an upload_only analysis result
        tags:
          - analysis
        parameters:
          - in: path
            name: analysis_resource_type
            required: true
            schema:
              type: string
            description: |
               What underlying data the analysis is on:
               must be "obj" (more to be added in the future)
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
            description: |
               The ID of the underlying data.
               This would be a string for an object ID.
          - in: path
            name: analysis_service_id
            required: true
            schema:
              type: string
            description: the analysis service id to be used
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  results:
                    type: object
                    description: Results data of this analysis
                  show_parameters:
                    type: boolean
                    description: Whether to render the parameters of this analysis
                  show_plots:
                    type: boolean
                    description: Whether to render the plots of this analysis
                  show_corner:
                    type: boolean
                    description: Whether to render the corner plots of this analysis
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups should be
                      able to view analysis results. Defaults to all of requesting user's
                      groups.
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
                            analysis_id:
                              type: integer
                              description: New analysis ID
        """
        # allowable resources now are [obj]. Can be extended in the future.
        if analysis_resource_type.lower() not in ['obj']:
            return self.error("Invalid analysis resource type", status=403)

        try:
            data = self.get_json()
        except Exception as e:
            return self.error(f'Error parsing JSON: {e}')

        with self.Session() as session:

            stmt = AnalysisService.select(self.current_user).where(
                AnalysisService.id == analysis_service_id
            )
            analysis_service = session.scalars(stmt).first()
            if analysis_service is None:
                return self.error(
                    message=f'Could not access Analysis Service ID: {analysis_service_id}.',
                    status=403,
                )
            if not analysis_service.upload_only:
                return self.error(
                    message=f'Analysis Service ID: {analysis_service_id} is not of type upload_only.',
                    status=403,
                )

            group_ids = data.pop('group_ids', None)
            if not group_ids:
                group_ids = [g.id for g in self.current_user.accessible_groups]

            groups = session.scalars(
                Group.select(self.current_user).where(Group.id.in_(group_ids))
            ).all()
            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.'
                )

            author = self.associated_user_object
            status_message = data.get("message", "")

            if analysis_resource_type.lower() == 'obj':
                obj_id = resource_id
                stmt = Obj.select(self.current_user).where(Obj.id == obj_id)
                obj = session.scalars(stmt).first()
                if obj is None:
                    return self.error(f'Obj {obj_id} not found', status=404)

                # make sure the user has not exceeded the maximum number of analyses
                # for this object. This will help save space on the disk
                # an enforce a reasonable limit on the number of analyses.
                stmt = ObjAnalysis.select(self.current_user).where(
                    ObjAnalysis.obj_id == obj_id
                )
                stmt = stmt.where(ObjAnalysis.author == author)
                stmt = stmt.where(ObjAnalysis.status == "completed")

                total_matches = session.execute(
                    select(func.count()).select_from(stmt)
                ).scalar()

                if (
                    total_matches
                    >= cfg["analysis_services.max_analysis_per_obj_per_user"]
                ):
                    return self.error(
                        (
                            'You have reached the maximum number of analyses for this object.'
                            ' Please delete some analyses before uploading more.'
                        ),
                        status=403,
                    )
                invalid_after = datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=10
                )
                analysis = ObjAnalysis(
                    obj=obj,
                    author=author,
                    groups=groups,
                    analysis_service=analysis_service,
                    show_parameters=data.get('show_parameters', True),
                    show_plots=data.get('show_plots', True),
                    show_corner=data.get('show_corner', True),
                    analysis_parameters={},
                    status='completed',
                    status_message=status_message,
                    handled_by_url="/",
                    invalid_after=invalid_after,
                    last_activity=datetime.datetime.utcnow(),
                )
            else:
                return self.error(
                    f'analysis_resource_type must be one of {", ".join(["obj"])}',
                    status=404,
                )
            session.add(analysis)
            try:
                session.commit()
            except IntegrityError as e:
                return self.error(f'Analysis already exists: {str(e)}')
            except Exception as e:
                return self.error(f'Unexpected error creating analysis: {str(e)}')

            results = data.get("analysis", {})
            if len(results.keys()) > 0:
                analysis._data = results
                analysis.save_data()
                message = f"Saved upload_only analysis data at {analysis.filename}. Message: {analysis.status_message}"
            else:
                message = f"Note: empty analysis upload_only results. Message: {analysis.status_message}"
            log(message)
            session.commit()
            return self.success(data={"id": analysis.id, "message": message})


class DefaultAnalysisHandler(BaseHandler):
    # this handler is a handler to post and get default analyses
    # a DefaultAnalysis is a reference to an analysis service, and a set of parameters, and a set of source_filter, that are criteria
    # for a default analysis to be run on an object

    @auth_or_token
    def get(self, analysis_service_id, default_analysis_id):
        """
        ---
        single:
          description: Retrieve a default analysis
          parameters:
            - in: path
              name: analysis_service_id
              required: true
              description: Analysis service ID
            - in: path
              name: default_analysis_id
              required: true
              description: Default analysis ID
          responses:
            200:
              content:
                application/json:
                  schema: SingleDefaultAnalysis
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all default analyses
          parameters:
            - in: path
              name: analysis_service_id
              required: false
              description: Analysis service ID, if not provided, return all default analyses for all analysis services
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfDefaultAnalysiss
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:
            try:
                if default_analysis_id is not None and analysis_service_id is not None:
                    stmt = DefaultAnalysis.select(self.current_user).where(
                        DefaultAnalysis.analysis_service_id == analysis_service_id,
                        DefaultAnalysis.id == default_analysis_id,
                    )
                    default_analysis = session.scalars(stmt).first()
                    if default_analysis is None:
                        return self.error(
                            f"Could not load default analysis {default_analysis_id}",
                            status=400,
                        )
                    return self.success(data=default_analysis)
                elif analysis_service_id is not None:
                    stmt = DefaultAnalysis.select(self.current_user).where(
                        DefaultAnalysis.analysis_service_id == analysis_service_id
                    )
                    default_analysis = session.scalars(stmt).all()
                    return self.success(data=default_analysis)
                else:
                    stmt = DefaultAnalysis.select(self.current_user)
                    default_analysis = session.scalars(stmt).all()
                    return self.success(data=default_analysis)
            except Exception as e:
                return self.error(
                    f'Unexpected error loading default analysis: {str(e)}'
                )

    @auth_or_token
    def post(self, analysis_service_id, default_analysis_id=None):
        data = self.get_json()
        with self.Session() as session:
            try:
                analysis_service = session.scalars(
                    AnalysisService.select(self.current_user).where(
                        AnalysisService.id == analysis_service_id
                    )
                ).first()
                if analysis_service is None:
                    return self.error(
                        f'Analysis service {analysis_service_id} not found', status=404
                    )

                stmt = DefaultAnalysis.select(self.current_user).where(
                    DefaultAnalysis.analysis_service_id == analysis_service_id,
                    DefaultAnalysis.author_id == self.associated_user_object.id,
                )
                default_analysis = session.scalars(stmt).first()
                if default_analysis is not None:
                    return self.error(
                        'You already have a default analysis for this analysis service. Delete it first, or update it.',
                        status=400,
                    )

                default_analysis_parameters = data.get(
                    'default_analysis_parameters', {}
                )
                source_filter = data.get('source_filter', {})
                daily_limit = data.get('daily_limit', 10)
                if not isinstance(daily_limit, int):
                    try:
                        daily_limit = int(daily_limit)
                    except Exception:
                        return self.error(
                            f'Invalid daily_limit: {daily_limit}.', status=400
                        )

                if daily_limit > DEFAULT_ANALYSES_DAILY_LIMIT or daily_limit <= 0:
                    return self.error(
                        f'Invalid daily_limit: {daily_limit}. Must be between 1 and {DEFAULT_ANALYSES_DAILY_LIMIT}',
                        status=400,
                    )

                stats = {
                    'daily_limit': daily_limit,
                    'daily_count': 0,
                    'last_run': datetime.datetime.utcnow().strftime(
                        "%Y-%m-%dT%H:%M:%S.%f"
                    ),
                }

                if not isinstance(source_filter, dict):
                    try:
                        source_filter = json.loads(source_filter)
                    except Exception:
                        return self.error(
                            f'Invalid source_filter: {source_filter}.',
                            status=400,
                        )

                if not isinstance(default_analysis_parameters, dict):
                    try:
                        default_analysis_parameters = json.loads(
                            default_analysis_parameters
                        )
                    except Exception:
                        return self.error(
                            f'Invalid analysis_parameters: {default_analysis_parameters}.',
                            status=400,
                        )

                if isinstance(analysis_service.optional_analysis_parameters, str):
                    optional_analysis_parameters = json.loads(
                        analysis_service.optional_analysis_parameters
                    )
                else:
                    optional_analysis_parameters = (
                        analysis_service.optional_analysis_parameters
                    )

                if not set(default_analysis_parameters.keys()).issubset(
                    set(optional_analysis_parameters.keys())
                ):
                    return self.error(
                        f'Invalid default_analysis_parameters: {default_analysis_parameters}.',
                        status=400,
                    )

                group_ids = data.pop('group_ids', None)
                if not group_ids:
                    group_ids = [g.id for g in self.current_user.accessible_groups]

                groups = session.scalars(
                    Group.select(self.current_user).where(Group.id.in_(group_ids))
                ).all()
                if {g.id for g in groups} != set(group_ids):
                    return self.error(
                        f'Cannot find one or more groups with IDs: {group_ids}.'
                    )

                # # check that the keys of the source_filter are valid from the enum DEFAULT_ANALYSIS_SOURCE_FILTERS
                if not set(source_filter.keys()).issubset(
                    set(DEFAULT_ANALYSIS_FILTER_TYPES.keys())
                ):
                    return self.error(f'Invalid source_filter: {source_filter}.')

                for key, value in source_filter.items():
                    if isinstance(value, list):
                        for v in value:
                            if isinstance(v, dict):
                                if not set(v.keys()).issubset(
                                    set(DEFAULT_ANALYSIS_FILTER_TYPES[key])
                                ):
                                    return self.error(
                                        f'Invalid source_filter. Key {key} must be a list of dicts with keys {str(DEFAULT_ANALYSIS_FILTER_TYPES[key])}.'
                                    )
                            else:
                                return self.error(
                                    f'Invalid source_filter. Key {key} must be a list of dicts.'
                                )
                    else:
                        return self.error(
                            f'Invalid source_filter with key {key}. Value must be a list.'
                        )

                author = self.associated_user_object

                default_analysis = DefaultAnalysis(
                    analysis_service=analysis_service,
                    default_analysis_parameters=default_analysis_parameters,
                    source_filter=source_filter,
                    stats=stats,
                    show_parameters=data.get('show_parameters', True),
                    show_plots=data.get('show_plots', True),
                    show_corner=data.get('show_corner', True),
                    author=author,
                    groups=groups,
                )

                session.add(default_analysis)
                session.commit()
                return self.success(data={"id": default_analysis.id})
            except Exception as e:
                raise e
                return self.error(
                    f'Unexpected error posting default analysis: {str(e)}'
                )

    @auth_or_token
    def delete(self, analysis_service_id, default_analysis_id):
        """
        ---
        description: Delete a default analysis
        parameters:
          - in: path
            name: analysis_service_id
            required: true
            schema:
              type: integer
            description: Analysis service ID
          - in: path
            name: default_analysis_id
            required: true
            schema:
              type: integer
            description: Default analysis ID
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        if default_analysis_id is None:
            return self.error("Missing required parameter: default_analysis_id")

        with self.Session() as session:
            try:
                default_analysis = session.scalars(
                    DefaultAnalysis.select(self.current_user).where(
                        DefaultAnalysis.analysis_service_id == analysis_service_id,
                        DefaultAnalysis.id == default_analysis_id,
                    )
                ).first()
                if default_analysis is None:
                    return self.error(
                        f"Could not find default analysis {default_analysis_id}",
                        status=400,
                    )
                session.delete(default_analysis)
                session.commit()
                return self.success()
            except Exception as e:
                return self.error(
                    f'Unexpected error deleting default analysis: {str(e)}'
                )
