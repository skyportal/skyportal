import json
from urllib.parse import urlparse

from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import IntegrityError

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.custom_exceptions import AccessError
from baselayer.app.model_util import recursive_to_dict

from baselayer.log import make_log
from baselayer.app.env import load_env

from ...enum_types import ANALYSIS_INPUT_TYPES, AUTHENTICATION_TYPES, ANALYSIS_TYPES

from ..base import BaseHandler

from ...models import (
    DBSession,
    AnalysisService,
    Group,
)

log = make_log('app/analysis')

_, cfg = load_env()


def valid_url(trial_url):
    """
    determine if the URL is valid
    """
    try:
        rez = urlparse(trial_url)
        return all([rez.scheme, rez.netloc])
    except ValueError:
        return False


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
        analysis_service = AnalysisService.get_if_accessible_by(
            analysis_service_id, self.current_user, mode="delete", raise_if_none=True
        )
        DBSession().delete(analysis_service)
        self.verify_and_commit()

        return self.success()
