import json
from urllib.parse import urlparse, urljoin
import datetime
import functools

import pandas as pd
import requests
from requests_oauthlib import OAuth1
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from tornado.ioloop import IOLoop
from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, scoped_session

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.custom_exceptions import AccessError
from baselayer.app.model_util import recursive_to_dict

from baselayer.log import make_log
from baselayer.app.env import load_env
from ...app_utils import get_app_base_url

from ...enum_types import ANALYSIS_INPUT_TYPES, AUTHENTICATION_TYPES, ANALYSIS_TYPES

from ..base import BaseHandler

from ...models import (
    DBSession,
    AnalysisService,
    Group,
    Photometry,
    Spectrum,
    Annotation,
    Classification,
    Obj,
    Comment,
    ObjAnalysis,
)
from .photometry import serialize

log = make_log('app/analysis')

_, cfg = load_env()

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))


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
        if not group_ids:
            groups = self.current_user.accessible_groups
        else:
            try:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible groups.', status=403)

        schema = AnalysisService.__schema__()
        try:
            analysis_service = schema.load(data)
        except ValidationError as e:
            return self.error(
                "Invalid/missing parameters: " f"{e.normalized_messages()}"
            )

        DBSession().add(analysis_service)
        analysis_service.groups = groups

        try:
            self.verify_and_commit()
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
        if analysis_service_id is not None:
            try:
                s = AnalysisService.get_if_accessible_by(
                    analysis_service_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Cannot access this Analysis Service.', status=403)

            analysis_dict = recursive_to_dict(s)
            analysis_dict["groups"] = s.groups
            return self.success(data=analysis_dict)

        # retrieve multiple services
        analysis_services = AnalysisService.get_records_accessible_by(self.current_user)
        self.verify_and_commit()

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

        # make sure we can update this analysis service
        _ = AnalysisService.get_if_accessible_by(
            analysis_service_id, self.current_user, mode="update", raise_if_none=True
        )

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
        DBSession().merge(new_analysis_service)

        if group_ids is not None:
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if not groups:
                return self.error(
                    "Invalid group_ids field. Specify at least one valid group ID."
                )
            if not all(
                [group in self.current_user.accessible_groups for group in groups]
            ):
                return self.error(
                    "Cannot change groups for Analysis Services that you are not a member of."
                )
            new_analysis_service.groups = groups

        self.verify_and_commit()
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
        try:
            analysis_service = AnalysisService.get_if_accessible_by(
                analysis_service_id,
                self.current_user,
                mode="delete",
                raise_if_none=True,
            )
        except AccessError:
            return self.error('Cannot delete this Analysis Service.', status=403)
        except Exception as e:
            return self.error(f'Error deleting Analysis Service: {e}')

        DBSession().delete(analysis_service)
        self.verify_and_commit()

        self.push_all(action='skyportal/REFRESH_ANALYSIS_SERVICES')
        return self.success()


class AnalysisHandler(BaseHandler):
    def generic_serialize(self, row, columns):
        return {c: getattr(row, c) for c in columns}

    def get_associated_obj_resource(self, associated_resource_type):
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
            input_data_types = analysis_service.input_data_types.copy()

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

            data["groups"] = groups
            author = self.associated_user_object
            data["author"] = author

            inputs = {"analysis_parameters": analysis_parameters}

            if analysis_resource_type.lower() == 'obj':
                obj_id = resource_id
                stmt = Obj.select(self.current_user).where(Obj.id == obj_id)
                obj = session.scalars(stmt).first()
                if obj is None:
                    return self.error(f'Obj {obj_id} not found', status=404)
                data["obj_id"] = obj_id
                data["obj"] = obj

                # Let's assemble the input data for this Obj
                for input_type in input_data_types:
                    associated_resource = self.get_associated_obj_resource(input_type)
                    stmt = (
                        associated_resource['class']
                        .select(self.current_user)
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
                        input_data = [
                            serialize(phot, 'ab', 'both') for phot in input_data
                        ]
                        df = pd.DataFrame(input_data)[
                            associated_resource['allowed_export_columns']
                        ]
                    else:
                        input_data = [
                            self.generic_serialize(
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
                    show_parameters=data.get('show_parameters', True),
                    show_plots=data.get('show_plots', True),
                    show_corner=data.get('show_corner', True),
                    analysis_parameters=analysis_parameters,
                    status='queued',
                    handled_by_url="api/webhook/obj_analysis",
                    invalid_after=invalid_after,
                )
            # Add more analysis_resource_types here one day (eg. GCN)
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

            self.push_notification(
                'Sending data to analysis service to start the analysis.',
            )

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
                with self.Session() as session:
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
                        analysis.status = (
                            'pending' if result.status_code == 200 else 'failure'
                        )
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

            # Start the analysis service in a separate thread and log any exceptions
            x = IOLoop.current().run_in_executor(None, external_analysis_service)
            x.add_done_callback(analysis_done_callback)

            return self.success(data={"id": analysis.id})

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
        include_filename = self.get_query_argument("includeFilename", False) in [
            "True",
            "t",
            "true",
            "1",
            True,
            1,
        ]
        obj_id = self.get_query_argument('objID', None)

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
                    analysis = session.scalars(stmt).first()
                    if analysis is None:
                        return self.error('Cannot access this Analysis.', status=403)

                    analysis_dict = recursive_to_dict(analysis)
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
                analyses = session.scalars(stmt).all()

                ret_array = []
                analysis_services_dict = {}
                for a in analyses:
                    analysis_dict = recursive_to_dict(a)
                    if a.analysis_service_id not in analysis_services_dict.keys():
                        stmt = AnalysisService.select(self.current_user).where(
                            AnalysisService.id == a.analysis_service_id
                        )
                        analysis_service = session.scalars(stmt).first()
                        analysis_services_dict.update(
                            {
                                a.analysis_service_id: {
                                    "analysis_service_name": analysis_service.display_name,
                                    "analysis_service_description": analysis_service.description,
                                }
                            }
                        )

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
                stmt = ObjAnalysis.select(self.current_user).where(
                    ObjAnalysis.id == analysis_id
                )
                analysis = session.scalars(stmt).first()
                if analysis is None:
                    return self.error('Cannot access this Analysis.', status=403)
                session.delete(analysis)
                session.commit()
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
                  plot_kwargs:
                    type: object
                    additionalProperties:
                      type: object
                    description: |
                        Extra parameters to pass to the plotting functions
                        if new plots are to be generated (e.g. with corner plots)
        responses:
          200:
            description: PNG finding chart file
            content:
                oneOf:
                    - image/png:
                        schema:
                            type: string
                            format: binary
                    - application/json:
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
                    elif product_type.lower() == "results":
                        if not analysis.has_results_data:
                            return self.error(
                                "No results data found for this Analysis.", status=404
                            )
                        return self.success(data=analysis.serialize_results_data())
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
