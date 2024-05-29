import asyncio
import sqlalchemy as sa
from marshmallow import Schema, fields, validates_schema
from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.flow import Flow
from baselayer.log import make_log
from ..base import BaseHandler

from ...models import (
    GcnEvent,
    Localization,
    SourcesConfirmedInGCN,
    TNSRobot,
    TNSRobotSubmission,
)
from ...utils.UTCTZnaiveDateTime import UTCTZnaiveDateTime

log = make_log('api/sources_confirmed_in_gcn')


class Validator(Schema):
    method = fields.Str(required=True)
    dateobs = UTCTZnaiveDateTime(required=True)
    source_id = fields.String()
    start_date = UTCTZnaiveDateTime(required=False, missing=None)
    end_date = UTCTZnaiveDateTime(required=False, missing=None)
    confirmed = fields.Boolean(
        truthy=['true', 'True', 'confirmed', True],
        falsy=['false', 'False', 'rejected', False],
        required=False,
    )
    explanation = fields.String(required=False)
    notes = fields.String(required=False)
    localization_name = fields.String()
    localization_cumprob = fields.Float()
    sources_id_list = fields.String()

    @validates_schema
    def validate_requires(self, data, **kwargs):
        if 'method' not in data:
            raise ValidationError('method is required')
        if data['method'] not in ['POST', 'GET', 'PATCH', 'DELETE']:
            raise ValidationError('method must be one of POST, GET, PATCH or DELETE')
        if data['method'] == 'GET':
            if 'sources_id_list' not in data:
                raise ValidationError('Missing required fields')
            if data['sources_id_list'] is None:
                raise ValidationError('Missing required fields')
        if data['method'] == 'POST':
            if (
                'start_date' not in data
                or 'end_date' not in data
                or 'localization_name' not in data
                or 'localization_cumprob' not in data
            ):
                raise ValidationError('Missing required fields')
            if (
                data['start_date'] is None
                or data['end_date'] is None
                or data['localization_name'] is None
                or data['localization_cumprob'] is None
            ):
                raise ValidationError('Missing required fields')
        if (
            data['method'] == 'PATCH'
            or data['method'] == 'DELETE'
            or data['method'] == 'POST'
        ):
            if 'source_id' not in data:
                raise ValidationError('Missing required fields')
            if data['source_id'] is None:
                raise ValidationError('Missing required fields')


class SourcesConfirmedInGCNHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs, source_id=None):
        """
        ---
        single:
          tags:
            - source_confirmed_in_gcn
          description: Retrieve a source that has been confirmed or rejected in a GCN
          parameters:
            - in: path
              name: dateobs
              required: true
              schema:
                type: string
              description: The dateobs of the event, as an arrow parseable string
            - in: path
              name: source_id
              required: false
              schema:
                type: string
              description: The source_id of the source to retrieve
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
                                description: the id of the confirmed_source_in_gcn
                              obj_id:
                                type: string
                                description: the source_id of the source
                              dateobs:
                                type: string
                                description: dateobs of the GCN evn
                              confirmed:
                                type: boolean
                                description: Boolean indicating whether the source is confirmed (True) or rejected (False)
            400:
              content:
                application/json:
                  schema: Error

        multiple:
          tags:
            - sources_confirmed_in_gcn
          description: Retrieve sources that have been confirmed/rejected in a GCN
          parameters:
            - in: path
              name: dateobs
              required: true
              schema:
                type: string
              description: The dateobs of the event, as an arrow parseable string
            - in: query
              name: sourcesIDList
              nullable: true
              schema:
                type: string
              description: |
                  A comma-separated list of source_id's to retrieve.
                  If not provided, all sources confirmed or rejected in GCN will be returned.
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
                            type: array
                            items:
                              id:
                                type: integer
                                description: the id of the confirmed_source_in_gcn
                              obj_id:
                                type: string
                                description: the source_id of the source
                              dateobs:
                                type: string
                                description: dateobs of the GCN evn
                              confirmed:
                                type: boolean
                                description: Whether the source is confirmed (True) or rejected (False)

            400:
              content:
                application/json:
                  schema: Error
        """
        sources_id_list = self.get_query_argument('sourcesIDList', '')
        if source_id is not None:
            sources_id_list = source_id
        validator_instance = Validator()
        params_to_be_validated = {
            'method': 'GET',
            'sources_id_list': sources_id_list,
            'dateobs': dateobs,
        }
        try:
            validated = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')
        dateobs = validated['dateobs']
        sources_id_list = validated['sources_id_list']

        if sources_id_list != '':
            try:
                sources_id_list = [
                    source_id.strip() for source_id in sources_id_list.split(',')
                ]
            except ValueError:
                return self.error(
                    "some of the sourceIDs in the sourcesIDList are not valid strings"
                )

        with self.Session() as session:
            try:
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                gcn_event = session.scalars(stmt).first()
                if not gcn_event:
                    return self.error(f"GCN event not found for dateobs: {dateobs}")

                if len(sources_id_list) == 0:
                    stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                        SourcesConfirmedInGCN.dateobs == dateobs
                    )
                else:
                    stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                        SourcesConfirmedInGCN.dateobs == dateobs,
                        SourcesConfirmedInGCN.obj_id.in_(sources_id_list),
                    )
                sources_in_gcn = session.scalars(stmt).all()
            except Exception as e:
                return self.error(str(e))

        return self.success(data=sources_in_gcn)

    @permissions(['Manage GCNs'])
    async def post(self, dateobs):
        """
        ---
        description: Confirm or reject a source in a gcn
        tags:
          - source_confirmed_in_gcn
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
            description: The dateobs of the event, as an arrow parseable string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  localization_name:
                    type: string
                    description: The name of the localization of the event
                  localization_cumprob:
                    type: string
                    description: The cumprob of the localization of the event
                  source_id:
                    type: string
                    description: The source_id of the source to confirm or reject
                  confirmed:
                    type: boolean
                    description: Whether the source is confirmed (True) or rejected (False)
                  start_date:
                    type: string
                    description: Choose sources with a first detection after start_date, as an arrow parseable string
                  end_date:
                    type: string
                    description: Choose sources with a last detection before end_date, as an arrow parseable string
                required:
                  - localization_name
                  - localization_cumprob
                  - source_id
                  - confirmed
                  - start_date
                  - end_date
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
                              type: int
                              description: The id of the source_confirmed_in_gcn
          400:
            content:
              application/json:
                schema: Error

        """
        data = self.get_json()

        localization_name = data.get('localization_name')
        localization_cumprob = data.get('localization_cumprob')
        source_id = data.get('source_id')
        confirmed = data.get('confirmed')
        explanation = data.get('explanation')
        notes = data.get('notes')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        validator_instance = Validator()
        params_to_be_validated = {
            'method': 'POST',
            'source_id': source_id,
            'dateobs': dateobs,
            'start_date': start_date,
            'end_date': end_date,
            'localization_name': localization_name,
            'localization_cumprob': localization_cumprob,
        }
        try:
            validated = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')

        source_id = validated['source_id']
        dateobs = validated['dateobs']
        start_date = validated['start_date']
        end_date = validated['end_date']
        localization_name = validated['localization_name']
        localization_cumprob = validated['localization_cumprob']

        source_in_gcn_id = None
        obj_internal_key = None

        with self.Session() as session:
            try:
                stmt = Localization.select(session.user_or_token).where(
                    Localization.localization_name == localization_name,
                    Localization.dateobs == dateobs,
                )
                localization = session.scalars(stmt).first()
                if not localization:
                    return self.error("Localization not found")

                stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                    SourcesConfirmedInGCN.dateobs == dateobs,
                    SourcesConfirmedInGCN.obj_id == source_id,
                )
                source_in_gcn = session.scalars(stmt).first()
                if source_in_gcn:
                    # if the status and explanation are the same, do nothing
                    if (
                        source_in_gcn.confirmed == confirmed
                        and source_in_gcn.explanation == explanation
                        and source_in_gcn.notes == notes
                    ):
                        return self.error(
                            "Source is already confirmed/rejected in this localization with the same explanation and notes"
                        )
                    # otherwise, update the status and explanation
                    else:
                        source_in_gcn.confirmed = confirmed
                        source_in_gcn.confirmer_id = self.associated_user_object.id
                        if explanation is not None:
                            source_in_gcn.explanation = explanation
                        if notes is not None:
                            source_in_gcn.notes = notes
                        session.commit()
                        source_in_gcn_id = source_in_gcn.id
                        obj_internal_key = source_in_gcn.obj.internal_key
                        if confirmed is True:
                            crossmatches = source_in_gcn.obj.gcn_crossmatch
                            if crossmatches is None:
                                crossmatches = [dateobs]
                            elif dateobs not in crossmatches:
                                crossmatches.append(dateobs)
                            setattr(source_in_gcn.obj, 'gcn_crossmatch', crossmatches)
                            session.commit()
                        else:
                            crossmatches = source_in_gcn.obj.gcn_crossmatch
                            if (
                                crossmatches is not None
                                and dateobs.strftime("%Y-%m-%d %H:%M:%S")
                                in crossmatches
                            ):
                                crossmatches.remove(
                                    dateobs.strftime("%Y-%m-%d %H:%M:%S")
                                )
                                if len(crossmatches) == 0:
                                    setattr(source_in_gcn.obj, 'gcn_crossmatch', None)
                                else:
                                    setattr(
                                        source_in_gcn.obj,
                                        'gcn_crossmatch',
                                        crossmatches,
                                    )
                                session.commit()
                else:
                    source_in_gcn = SourcesConfirmedInGCN(
                        obj_id=source_id,
                        dateobs=dateobs,
                        confirmed=confirmed,
                        confirmer_id=self.associated_user_object.id,
                    )
                    if explanation is not None:
                        source_in_gcn.explanation = explanation
                    if notes is not None:
                        source_in_gcn.notes = notes
                    session.add(source_in_gcn)
                    session.commit()
                    source_in_gcn_id = source_in_gcn.id
                    obj_internal_key = source_in_gcn.obj.internal_key
                    if confirmed is True:
                        crossmatches = source_in_gcn.obj.gcn_crossmatch
                        if crossmatches is None:
                            crossmatches = [dateobs]
                        elif dateobs not in crossmatches:
                            crossmatches.append(dateobs)
                        setattr(source_in_gcn.obj, 'gcn_crossmatch', crossmatches)
                        session.commit()
                    else:
                        crossmatches = source_in_gcn.obj.gcn_crossmatch
                        if (
                            crossmatches is not None
                            and dateobs.strftime("%Y-%m-%d %H:%M:%S") in crossmatches
                        ):
                            crossmatches.remove(dateobs.strftime("%Y-%m-%d %H:%M:%S"))
                            if len(crossmatches) == 0:
                                setattr(source_in_gcn.obj, 'gcn_crossmatch', None)
                            else:
                                setattr(
                                    source_in_gcn.obj, 'gcn_crossmatch', crossmatches
                                )
                            session.commit()

            except Exception as e:
                session.rollback()
                return self.error(str(e))

        if obj_internal_key is not None:
            flow = Flow()
            flow.push(
                '*', "skyportal/REFRESH_SOURCE", payload={"obj_key": obj_internal_key}
            )

        return self.success(data={'id': source_in_gcn_id})

    @permissions(['Manage GCNs'])
    def patch(self, dateobs, source_id):
        """
        ---
        description: Update the confirmed or rejected status of a source in a GCN
        tags:
          - source_confirmed_in_gcn
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: source_id
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  confirmed:
                    type: boolean
                    description: Whether the source is confirmed (True) or rejected (False)
                required:
                  - confirmed

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
                              type: int
                              description: The id of the modified source_confirmed_in_gcn
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        confirmed = data.get('confirmed')
        explanation = data.get('explanation')
        notes = data.get('notes')

        validator_instance = Validator()
        params_to_be_validated = {
            'method': 'PATCH',
            'source_id': source_id,
            'dateobs': dateobs,
        }
        if explanation is not None:
            params_to_be_validated["explanation"] = explanation
        try:
            validated = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')

        source_id = validated['source_id'].strip()
        dateobs = validated['dateobs']

        source_in_gcn_id = None
        obj_internal_key = None

        with self.Session() as session:
            try:
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                gcn_event = session.scalars(stmt).first()
                if not gcn_event:
                    return self.error(f"GCN event not found for dateobs: {dateobs}")

                stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                    SourcesConfirmedInGCN.dateobs == dateobs,
                    SourcesConfirmedInGCN.obj_id == source_id,
                )
                source_in_gcn = session.scalars(stmt).first()
                if not source_in_gcn:
                    return self.error(
                        "Source is not confirmed/rejected in this GCN event"
                    )
                source_in_gcn.confirmed = confirmed
                source_in_gcn.confirmer_id = self.associated_user_object.id
                if explanation is not None:
                    source_in_gcn.explanation = explanation
                if notes is not None:
                    source_in_gcn.notes = notes
                session.commit()
                source_in_gcn_id = source_in_gcn.id
                obj_internal_key = source_in_gcn.obj.internal_key
                if confirmed is True:
                    crossmatches = source_in_gcn.obj.gcn_crossmatch
                    if crossmatches is None:
                        crossmatches = [dateobs]
                    elif dateobs not in crossmatches:
                        crossmatches.append(dateobs)
                    setattr(source_in_gcn.obj, 'gcn_crossmatch', crossmatches)
                    session.commit()
                else:
                    crossmatches = source_in_gcn.obj.gcn_crossmatch
                    if (
                        crossmatches is not None
                        and dateobs.strftime("%Y-%m-%d %H:%M:%S") in crossmatches
                    ):
                        crossmatches.remove(dateobs.strftime("%Y-%m-%d %H:%M:%S"))
                        if len(crossmatches) == 0:
                            setattr(source_in_gcn.obj, 'gcn_crossmatch', None)
                        else:
                            setattr(source_in_gcn.obj, 'gcn_crossmatch', crossmatches)
                        session.commit()
            except Exception as e:
                session.rollback()
                return self.error(str(e))

        if obj_internal_key is not None:
            flow = Flow()
            flow.push(
                '*', "skyportal/REFRESH_SOURCE", payload={"obj_key": obj_internal_key}
            )

        return self.success(data={'id': source_in_gcn_id})

    @permissions(['Manage GCNs'])
    def delete(self, dateobs, source_id):
        """
        ---
        description: |
          Deletes the confirmed or rejected status of source in a GCN.
          Its status can be considered as 'undefined'.
        tags:
          - source_confirmed_in_gcn
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
          - in: path
            name: source_id
            required: true
            schema:
              type: string
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
                              type: int
                              description: The id of the deleted source_confirmed_in_gcn
          400:
            content:
              application/json:
                schema: Error
        """

        validator_instance = Validator()
        params_to_be_validated = {
            'method': 'DELETE',
            'source_id': source_id,
            'dateobs': dateobs,
        }
        try:
            validated = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')

        source_id = validated['source_id'].strip()
        dateobs = validated['dateobs']

        source_in_gcn_id = None
        obj_internal_key = None

        with self.Session() as session:
            try:
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                gcn_event = session.scalars(stmt).first()
                if not gcn_event:
                    return self.error(f"GCN event not found for dateobs: {dateobs}")
                stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                    SourcesConfirmedInGCN.obj_id == source_id,
                    SourcesConfirmedInGCN.dateobs == dateobs,
                )
                source_in_gcn = session.scalars(stmt).first()
                if not source_in_gcn:
                    return self.error(
                        "Source is not confirmed or rejected in this GCN event"
                    )
                crossmatches = source_in_gcn.obj.gcn_crossmatch
                if (
                    crossmatches is not None
                    and dateobs.strftime("%Y-%m-%d %H:%M:%S") in crossmatches
                ):
                    crossmatches.remove(dateobs.strftime("%Y-%m-%d %H:%M:%S"))
                    if len(crossmatches) == 0:
                        setattr(source_in_gcn.obj, 'gcn_crossmatch', None)
                    else:
                        setattr(source_in_gcn.obj, 'gcn_crossmatch', crossmatches)
                    session.commit()
                source_in_gcn_id = source_in_gcn.id
                obj_internal_key = source_in_gcn.obj.internal_key
                session.delete(source_in_gcn)
                session.commit()
            except Exception as e:
                session.rollback()
                return self.error(str(e))

        if obj_internal_key is not None:
            flow = Flow()
            flow.push(
                '*', "skyportal/REFRESH_SOURCE", payload={"obj_key": obj_internal_key}
            )
        return self.success(data={'id': source_in_gcn_id})


class SourcesConfirmedInGCNTNSHandler(BaseHandler):
    @auth_or_token
    async def post(self, dateobs):
        """
        ---
        tags:
          - sources_confirmed_in_gcn
        description: Post sources that have been confirmed in a GCN to TNS
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
            description: The dateobs of the event, as an arrow parseable string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  tnsrobotID:
                    type: int
                    description: |
                      TNS Robot ID.
                  reporters:
                    type: string
                    description: |
                      Reporters for the TNS report.
                  archival:
                    type: boolean
                    description: |
                      Report sources as archival (i.e. no upperlimit).
                      Defaults to False.
                  archivalComment:
                    type: string
                    description: |
                      Comment on archival source. Required if archival is True.
                  sourcesIDList:
                    type: string
                    description: |
                      A comma-separated list of source_id's to post.
                      If not provided, all sources confirmed in GCN will be posted.
                  confirmed:
                    type: boolean
                    description: |
                      Only post sources noted as confirmed / highlighted.
                      Defaults to True.
                required:
                  - tnsrobotID
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

        data = self.get_json()
        sources_id_list = data.get('sourcesIDList', '')
        confirmed = data.get('confirmed', True)
        tnsrobotID = data.get('tnsrobotID')
        reporters = data.get('reporters', '')
        remarks = data.get('remarks', '')
        archival = data.get('archival', False)
        archival_comment = data.get('archivalComment', '')

        if tnsrobotID is None:
            return self.error('tnsrobotID is required')
        if reporters == '' or not isinstance(reporters, str):
            return self.error('reporters is required and must be a non-empty string')

        if sources_id_list != '':
            try:
                sources_id_list = [
                    source_id.strip() for source_id in sources_id_list.split(',')
                ]
            except ValueError:
                return self.error(
                    "some of the sourceIDs in the sourcesIDList are not valid strings"
                )

        with self.Session() as session:
            try:
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                gcn_event = session.scalars(stmt).first()
                if not gcn_event:
                    return self.error(f"GCN event not found for dateobs: {dateobs}")

                if len(sources_id_list) == 0:
                    stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                        SourcesConfirmedInGCN.dateobs == dateobs
                    )
                else:
                    stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                        SourcesConfirmedInGCN.dateobs == dateobs,
                        SourcesConfirmedInGCN.obj_id.in_(sources_id_list),
                    )
                if confirmed:
                    stmt = stmt.where(SourcesConfirmedInGCN.confirmed.is_(True))
                sources_in_gcn = session.scalars(stmt).all()

                tnsrobot = session.scalars(
                    TNSRobot.select(session.user_or_token).where(
                        TNSRobot.id == tnsrobotID
                    )
                ).first()
                if tnsrobot is None:
                    return self.error(f'No TNSRobot available with ID {tnsrobotID}')

                if archival is True:
                    if len(archival_comment) == 0:
                        return self.error(
                            'If source flagged as archival, archival_comment is required'
                        )

                altdata = tnsrobot.altdata
                if not altdata:
                    return self.error('Missing TNS information.')
                if 'api_key' not in altdata:
                    return self.error('Missing TNS API key.')

                try:
                    loop = asyncio.get_event_loop()
                except Exception:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                obj_with_requests = []
                for obj in sources_in_gcn:
                    # verify that there isn't already a TNSRobotSubmission for this object
                    # and TNSRobot, that is:
                    # 1. pending
                    # 2. processing
                    # 3. submitted
                    # 4. complete
                    # if so, do not add another request
                    existing_submission_request = session.scalars(
                        TNSRobotSubmission.select(session.user_or_token).where(
                            TNSRobotSubmission.obj_id == obj.id,
                            TNSRobotSubmission.tnsrobot_id == tnsrobot.id,
                            sa.or_(
                                TNSRobotSubmission.status == "pending",
                                TNSRobotSubmission.status == "processing",
                                TNSRobotSubmission.status.like("submitted%"),
                                TNSRobotSubmission.status.like("complete%"),
                            ),
                        )
                    ).first()
                    if existing_submission_request is not None:
                        log(
                            f"Skipping TNSRobotSubmission request for obj_id {obj.id} with tnsrobot_id {tnsrobot.id} for user_id {self.associated_user_object.id} as there is already a submission request with status {existing_submission_request.status}"
                        )
                        continue
                    submission = TNSRobotSubmission(
                        tnsrobot_id=tnsrobot.id,
                        obj_id=obj.obj_id,
                        user_id=self.associated_user_object.id,
                        custom_reporting_string=reporters,
                        custom_remarks_string=remarks,
                        archival=archival,
                        archival_comment=archival_comment,
                        auto_submission=False,
                    )
                    session.add(submission)
                    log(
                        f"Added TNSRobotSubmission request for obj_id {obj.id} confirmed in GCN with tnsrobot_id {tnsrobot.id} for user_id {self.associated_user_object.id}"
                    )
                    obj_with_requests.append(obj.obj_id)
                session.commit()

                return self.success(data={'obj_ids': obj_with_requests})

            except Exception as e:
                return self.error(str(e))


class GCNsAssociatedWithSourceHandler(BaseHandler):
    @auth_or_token
    async def get(self, source_id):
        """
        ---
        description: Get the GCNs associated with a source (GCNs for which the source has been confirmed)
        tags:
          - gcn_associated_to_source
        parameters:
          - in: path
            name: source_id
            required: true
            schema:
              type: string
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
                            gcns:
                              type: array
                              items:
                                type: string
                                description: GCNs dateobs
          400:
            content:
              application/json:
                schema: Error
        """
        if not isinstance(source_id, str):
            return self.error("source_id must be a string")

        source_id = source_id.strip()

        with self.Session() as session:
            try:
                stmt = SourcesConfirmedInGCN.select(session.user_or_token).where(
                    SourcesConfirmedInGCN.obj_id == source_id,
                    SourcesConfirmedInGCN.confirmed.is_(True),
                )
                source_confirmed_in_gcns = session.scalars(stmt.distinct()).all()
                gcns = [
                    source_confirmed_in_gcn.dateobs
                    for source_confirmed_in_gcn in source_confirmed_in_gcns
                ]
                gcns = list(set(gcns))

            except Exception as e:
                return self.error(str(e))
        return self.success(data={"gcns": gcns})
