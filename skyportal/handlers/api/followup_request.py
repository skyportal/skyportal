import arrow
import jsonschema
from marshmallow.exceptions import ValidationError
import io
from tornado.ioloop import IOLoop
import pandas as pd
import tempfile
import functools

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.coordinates import EarthLocation
from astropy.time import Time, TimeDelta

from astroplan import Observer
from astroplan import FixedTarget
from astroplan import ObservingBlock
from astroplan.constraints import (
    AtNightConstraint,
    AirmassConstraint,
    MoonSeparationConstraint,
)
from astroplan.scheduling import Transitioner
from astroplan.scheduling import PriorityScheduler
from astroplan.scheduling import Schedule
from astroplan.plots import plot_schedule_airmass

import matplotlib
import matplotlib.pyplot as plt

from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    FollowupRequest,
    Instrument,
    ClassicalAssignment,
    ObservingRun,
    Obj,
    Group,
    Allocation,
)

from sqlalchemy.orm import joinedload

from ...models.schema import AssignmentSchema, FollowupRequestPost


class AssignmentHandler(BaseHandler):
    @auth_or_token
    def get(self, assignment_id=None):
        """
        ---
        single:
          description: Retrieve an observing run assignment
          tags:
            - assignments
          parameters:
            - in: path
              name: assignment_id
              required: true
              schema:
                type: integer
          responses:
            200:
               content:
                application/json:
                  schema: SingleClassicalAssignment
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all observing run assignments
          tags:
            - assignments
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfClassicalAssignments
            400:
              content:
                application/json:
                  schema: Error
        """

        # get owned assignments
        assignments = ClassicalAssignment.query_records_accessible_by(self.current_user)

        if assignment_id is not None:
            try:
                assignment_id = int(assignment_id)
            except ValueError:
                return self.error("Assignment ID must be an integer.")

            assignments = assignments.filter(
                ClassicalAssignment.id == assignment_id
            ).options(
                joinedload(ClassicalAssignment.obj).joinedload(Obj.thumbnails),
                joinedload(ClassicalAssignment.requester),
                joinedload(ClassicalAssignment.obj),
            )

        assignments = assignments.all()

        if len(assignments) == 0 and assignment_id is not None:
            return self.error("Could not retrieve assignment.")

        out_json = ClassicalAssignment.__schema__().dump(assignments, many=True)

        # calculate when the targets rise and set
        for json_obj, assignment in zip(out_json, assignments):
            json_obj['rise_time_utc'] = assignment.rise_time.isot
            json_obj['set_time_utc'] = assignment.set_time.isot
            json_obj['obj'] = assignment.obj
            json_obj['requester'] = assignment.requester

        if assignment_id is not None:
            out_json = out_json[0]

        self.verify_and_commit()
        return self.success(data=out_json)

    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Post new target assignment to observing run
        tags:
          - assignments
        requestBody:
          content:
            application/json:
              schema: AssignmentSchema
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
                              description: New assignment ID
        """

        data = self.get_json()
        try:
            assignment = ClassicalAssignment(**AssignmentSchema.load(data=data))
        except ValidationError as e:
            return self.error(
                'Error parsing followup request: ' f'"{e.normalized_messages()}"'
            )

        run_id = assignment.run_id
        data['priority'] = assignment.priority.name
        ObservingRun.get_if_accessible_by(run_id, self.current_user, raise_if_none=True)

        predecessor = (
            ClassicalAssignment.query_records_accessible_by(self.current_user)
            .filter(
                ClassicalAssignment.obj_id == assignment.obj_id,
                ClassicalAssignment.run_id == run_id,
            )
            .first()
        )

        if predecessor is not None:
            return self.error('Object is already assigned to this run.')

        assignment = ClassicalAssignment(**data)

        assignment.requester_id = self.associated_user_object.id
        DBSession().add(assignment)
        self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": assignment.obj.internal_key},
        )
        self.push_all(
            action="skyportal/REFRESH_OBSERVING_RUN",
            payload={"run_id": assignment.run_id},
        )
        return self.success(data={"id": assignment.id})

    @permissions(["Upload data"])
    def put(self, assignment_id):
        """
        ---
        description: Update an assignment
        tags:
          - assignments
        parameters:
          - in: path
            name: assignment_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: ClassicalAssignmentNoID
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
        assignment = ClassicalAssignment.get_if_accessible_by(
            int(assignment_id), self.current_user, mode="update", raise_if_none=True
        )

        data = self.get_json()
        data['id'] = assignment_id
        data["last_modified_by_id"] = self.associated_user_object.id

        schema = ClassicalAssignment.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": assignment.obj.internal_key},
        )
        self.push_all(
            action="skyportal/REFRESH_OBSERVING_RUN",
            payload={"run_id": assignment.run_id},
        )
        return self.success()

    @permissions(["Upload data"])
    def delete(self, assignment_id):
        """
        ---
        description: Delete assignment.
        tags:
          - assignments
        parameters:
          - in: path
            name: assignment_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        assignment = ClassicalAssignment.get_if_accessible_by(
            int(assignment_id), self.current_user, mode="delete", raise_if_none=True
        )
        obj_key = assignment.obj.internal_key
        DBSession().delete(assignment)
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": obj_key},
        )
        self.push_all(
            action="skyportal/REFRESH_OBSERVING_RUN",
            payload={"run_id": assignment.run_id},
        )
        return self.success()


class FollowupRequestHandler(BaseHandler):
    @auth_or_token
    def get(self, followup_request_id=None):
        """
        ---
        single:
          description: Retrieve a followup request
          tags:
            - followup_requests
          parameters:
            - in: path
              name: followup_request_id
              required: true
              schema:
                type: integer
          responses:
            200:
               content:
                application/json:
                  schema: SingleFollowupRequest
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all followup requests
          tags:
            - followup_requests
          parameters:
          - in: query
            name: sourceID
            nullable: true
            schema:
              type: string
            description: Portion of ID to filter on
          - in: query
            name: startDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              created_at >= startDate
          - in: query
            name: endDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              created_at <= endDate
          - in: query
            name: status
            nullable: true
            schema:
              type: string
            description: |
              String to match status of request against
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfFollowupRequests
            400:
              content:
                application/json:
                  schema: Error
        """

        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        sourceID = self.get_query_argument('sourceID', None)
        status = self.get_query_argument('status', None)

        # get owned assignments
        followup_requests = FollowupRequest.query_records_accessible_by(
            self.current_user
        )

        if followup_request_id is not None:
            try:
                followup_request_id = int(followup_request_id)
            except ValueError:
                return self.error("Assignment ID must be an integer.")

            followup_requests = followup_requests.filter(
                FollowupRequest.id == followup_request_id
            ).options(
                joinedload(FollowupRequest.obj).joinedload(Obj.thumbnails),
                joinedload(FollowupRequest.requester),
                joinedload(FollowupRequest.obj),
            )
            followup_request = followup_requests.first()
            if followup_request is None:
                return self.error("Could not retrieve followup request.")
            self.verify_and_commit()
            return self.success(data=followup_request)

        if start_date:
            start_date = str(arrow.get(start_date.strip()).datetime)
            followup_requests = followup_requests.filter(
                FollowupRequest.created_at >= start_date
            )
        if end_date:
            end_date = str(arrow.get(end_date.strip()).datetime)
            followup_requests = followup_requests.filter(
                FollowupRequest.created_at <= end_date
            )
        if sourceID:
            obj_query = Obj.query_records_accessible_by(self.current_user).filter(
                Obj.id.contains(sourceID.strip())
            )
            obj_subquery = obj_query.subquery()
            followup_requests = followup_requests.join(
                obj_subquery, FollowupRequest.obj_id == obj_subquery.c.id
            )
        if status:
            followup_requests = followup_requests.filter(
                FollowupRequest.status.contains(status.strip())
            )

        followup_requests = followup_requests.options(
            joinedload(FollowupRequest.allocation).joinedload(Allocation.instrument),
            joinedload(FollowupRequest.allocation).joinedload(Allocation.group),
            joinedload(FollowupRequest.obj),
            joinedload(FollowupRequest.requester),
        ).all()
        self.verify_and_commit()
        return self.success(data=followup_requests)

    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: Submit follow-up request.
        tags:
          - followup_requests
        requestBody:
          content:
            application/json:
              schema: FollowupRequestPost
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
                              description: New follow-up request ID
        """
        data = self.get_json()

        try:
            data = FollowupRequestPost.load(data)
        except ValidationError as e:
            return self.error(
                f'Invalid / missing parameters: {e.normalized_messages()}'
            )

        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = int(data['allocation_id'])

        allocation = Allocation.get_if_accessible_by(
            data['allocation_id'], self.current_user, raise_if_none=True
        )
        instrument = allocation.instrument

        if instrument.api_classname is None:
            return self.error('Instrument has no remote API.')

        if not instrument.api_class.implements()['submit']:
            return self.error('Cannot submit followup requests to this Instrument.')

        target_groups = []
        for group_id in data.pop('target_group_ids', []):
            g = Group.get_if_accessible_by(
                group_id, self.current_user, raise_if_none=True
            )
            target_groups.append(g)

        try:
            formSchema = instrument.api_class.custom_json_schema(instrument)
        except AttributeError:
            formSchema = instrument.api_class.form_json_schema

        # validate the payload
        jsonschema.validate(data['payload'], formSchema)

        followup_request = FollowupRequest.__schema__().load(data)
        followup_request.target_groups = target_groups
        DBSession().add(followup_request)
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": followup_request.obj.internal_key},
        )

        try:
            instrument.api_class.submit(followup_request)
        except Exception:
            followup_request.status = 'failed to submit'
            raise
        finally:
            self.verify_and_commit()
            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": followup_request.obj.internal_key},
            )

        return self.success(data={"id": followup_request.id})

    @permissions(["Upload data"])
    def put(self, request_id):
        """
        ---
        description: Update a follow-up request
        tags:
          - followup_requests
        parameters:
          - in: path
            name: request_id
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema: FollowupRequestPost
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
            request_id = int(request_id)
        except ValueError:
            return self.error('Request id must be an int.')

        followup_request = FollowupRequest.get_if_accessible_by(
            request_id, self.current_user, mode="update", raise_if_none=True
        )

        data = self.get_json()

        try:
            data = FollowupRequestPost.load(data)
        except ValidationError as e:
            return self.error(
                f'Invalid / missing parameters: {e.normalized_messages()}'
            )

        data['id'] = request_id
        data["last_modified_by_id"] = self.associated_user_object.id

        api = followup_request.instrument.api_class

        if not api.implements()['update']:
            return self.error('Cannot update requests on this instrument.')

        target_group_ids = data.pop('target_group_ids', None)
        if target_group_ids is not None:
            target_groups = []
            for group_id in target_group_ids:
                g = Group.get_if_accessible_by.get(
                    group_id, self.current_user, raise_if_none=True
                )
                target_groups.append(g)
            followup_request.target_groups = target_groups

        # validate posted data
        try:
            FollowupRequest.__schema__().load(data, partial=True)
        except ValidationError as e:
            return self.error(
                f'Error parsing followup request update: "{e.normalized_messages()}"'
            )

        for k in data:
            setattr(followup_request, k, data[k])

        followup_request.instrument.api_class.update(followup_request)
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": followup_request.obj.internal_key},
        )
        return self.success()

    @permissions(["Upload data"])
    def delete(self, request_id):
        """
        ---
        description: Delete follow-up request.
        tags:
          - followup_requests
        parameters:
          - in: path
            name: request_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        followup_request = FollowupRequest.get_if_accessible_by(
            request_id, self.current_user, mode="delete", raise_if_none=True
        )

        api = followup_request.instrument.api_class
        if not api.implements()['delete']:
            return self.error('Cannot delete requests on this instrument.')

        followup_request.last_modified_by_id = self.associated_user_object.id
        internal_key = followup_request.obj.internal_key

        api.delete(followup_request)
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": internal_key},
        )
        return self.success()


def observation_schedule(
    followup_requests,
    instrument,
    observation_start=Time.now(),
    observation_end=Time.now() + TimeDelta(12 * u.hour),
    output_format='csv',
    figsize=(10, 8),
):

    """Create a schedule to display observations for a particular instrument
    Parameters
    ----------
    followup_requests : skyportal.models.followup_request.FollowupRequest
        The planned observations associated with the request
    instrument : skyportal.models.instrument.Instrument
        The instrument that the request is made based on
    observation_start: astropy.time.Time
        Start time for the observations
    observation_end: astropy.time.Time
        End time for the observations
    output_format : str, optional
        "csv", "pdf" or "png" -- determines the format of the returned observation plan
    figsize : tuple, optional
        Matplotlib figsize of the pdf/png created
    Returns
    -------
    dict
        success : bool
            Whether the request was successful or not, returning
            a sensible error in 'reason'
        name : str
            suggested filename based on `instrument` and `output_format`
        data : str
            binary encoded data for the file (to be streamed)
        reason : str
            If not successful, a reason is returned.
    """

    location = EarthLocation.from_geodetic(
        instrument.telescope.lon * u.deg,
        instrument.telescope.lat * u.deg,
        instrument.telescope.elevation * u.m,
    )
    observer = Observer(location=location, name=instrument.name)

    global_constraints = [
        AirmassConstraint(max=2.50, boolean_constraint=False),
        AtNightConstraint.twilight_civil(),
        MoonSeparationConstraint(min=10.0 * u.deg),
    ]

    blocks = []
    read_out = 10.0 * u.s

    for ii, followup_request in enumerate(followup_requests):
        obj = followup_request.obj
        coord = SkyCoord(ra=obj.ra * u.deg, dec=obj.dec * u.deg)
        target = FixedTarget(coord=coord, name=obj.id)

        payload = followup_request.payload
        allocation = followup_request.allocation
        requester = followup_request.requester

        if "start_date" in payload:
            start_date = Time(payload["start_date"], format='isot')
            if start_date > observation_end:
                continue

        if "end_date" in payload:
            end_date = Time(payload["end_date"], format='isot')
            if end_date < observation_start:
                continue

        if "priority" in payload:
            priority = payload["priority"]
        else:
            priority = 1

        # make sure to invert priority (priority = 5.0 is max, priority = 1.0 is min)
        priority = 5.0 / priority

        if "exposure_time" in payload:
            exposure_time = payload["exposure_time"] * u.s
        else:
            exposure_time = 3600 * u.s

        if "exposure_counts" in payload:
            exposure_counts = payload["exposure_counts"]
        else:
            exposure_counts = 1

        # get extra constraints
        constraints = []
        if "minimum_lunar_distance" in payload:
            constraints.append(
                MoonSeparationConstraint(min=payload['minimum_lunar_distance'] * u.deg)
            )

        if "maximum_airmass" in payload:
            constraints.append(
                AirmassConstraint(
                    max=payload['maximum_airmass'], boolean_constraint=False
                )
            )

        if "observation_choices" in payload:
            configurations = [
                {
                    'requester': requester.username,
                    'group_id': allocation.group_id,
                    'request_id': followup_request.id,
                    'filter': bandpass,
                }
                for bandpass in payload["observation_choices"]
            ]
        else:
            configurations = [
                {
                    'requester': requester.username,
                    'group_id': allocation.group_id,
                    'request_id': followup_request.id,
                    'filter': 'default',
                }
            ]

        for configuration in configurations:
            b = ObservingBlock.from_exposures(
                target,
                priority,
                exposure_time,
                exposure_counts,
                read_out,
                configuration=configuration,
            )
            blocks.append(b)

    # Initialize a transitioner object with the slew rate and/or the
    # duration of other transitions (e.g. filter changes)
    slew_rate = 2.0 * u.deg / u.second
    transitioner = Transitioner(slew_rate, {'filter': {'default': 10 * u.second}})

    # Initialize the sequential scheduler with the constraints and transitioner
    prior_scheduler = PriorityScheduler(
        constraints=global_constraints, observer=observer, transitioner=transitioner
    )
    # Initialize a Schedule object, to contain the new schedule
    priority_schedule = Schedule(observation_start, observation_end)

    # Call the schedule with the observing blocks and schedule to schedule the blocks
    prior_scheduler(blocks, priority_schedule)

    if output_format in ["png", "pdf"]:
        matplotlib.use("Agg")
        fig = plt.figure(figsize=figsize, constrained_layout=False)
        plot_schedule_airmass(priority_schedule, show_night=True)
        plt.legend(loc="upper right")
        buf = io.BytesIO()
        fig.savefig(buf, format=output_format)
        plt.close(fig)
        buf.seek(0)

        return {
            "success": True,
            "name": f"schedule_{instrument.name}.{output_format}",
            "data": buf.read(),
            "reason": "",
        }
    elif output_format == "csv":
        try:
            schedule_table = priority_schedule.to_table(
                show_transitions=False, show_unused=False
            )
        except Exception as e:
            raise ValueError(
                f'Scheduling failed: there are probably no observable targets: {str(e)}.'
            )

        schedule = []
        for block in schedule_table:
            target = block["target"]
            if target == "TransitionBlock":
                continue

            filt = block["configuration"]["filter"]
            request_id = block["configuration"]["request_id"]
            group_id = block["configuration"]["group_id"]
            requester = block["configuration"]["requester"]

            obs_start = Time(block["start time (UTC)"], format='iso')
            obs_end = Time(block["end time (UTC)"], format='iso')
            exposure_time = int(block["duration (minutes)"] * 60.0)

            c = SkyCoord(
                ra=block["ra"] * u.degree, dec=block["dec"] * u.degree, frame='icrs'
            )
            ra = c.ra.to_string(unit=u.hour, sep=':')
            dec = c.dec.to_string(unit=u.degree, sep=':')

            observation = {
                'request_id': request_id,
                'group_id': group_id,
                'object_id': target,
                'ra': ra,
                'dec': dec,
                'epoch': 2000,
                'observation_start': obs_start,
                'observation_end': obs_end,
                'exposure_time': exposure_time,
                'filter': filt,
                'requester': requester,
            }
            schedule.append(observation)

        df = pd.DataFrame(schedule)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.' + output_format) as f:
            df.to_csv(f.name)
            f.flush()

            with open(f.name, mode='rb') as g:
                csv_content = g.read()

        return {
            "success": True,
            "name": f"schedule_{instrument.name}.{output_format}",
            "data": csv_content,
            "reason": "",
        }


class FollowupRequestSchedulerHandler(BaseHandler):
    @auth_or_token
    async def get(self, instrument_id):
        """
        ---
        description: Retrieve followup requests schedule
        tags:
            - followup_requests
        parameters:
        - in: query
          name: sourceID
          nullable: true
          schema:
            type: string
          description: Portion of ID to filter on
        - in: query
          name: startDate
          nullable: true
          schema:
            type: string
          description: |
            Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
            created_at >= startDate
        - in: query
          name: endDate
          nullable: true
          schema:
            type: string
          description: |
            Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
            created_at <= endDate
        - in: query
          name: status
          nullable: true
          schema:
            type: string
          description: |
            String to match status of request against
        - in: query
          name: observationStartDate
          nullable: true
          schema:
            type: string
          description: |
            Arrow-parseable date string (e.g. 2020-01-01). If provided, start time
            of observation window, otherwise now.
        - in: query
          name: observationEndDate
          nullable: true
          schema:
            type: string
          description: |
            Arrow-parseable date string (e.g. 2020-01-01). If provided, end time
            of observation window, otherwise 12 hours from now.
        - in: query
          name: output_format
          nullable: true
          schema:
            type: string
          description: |
            Output format for schedule. Can be png, pdf, or csv
        responses:
          200:
            description: A PDF/PNG schedule file
            content:
              application/pdf:
                schema:
                  type: string
                  format: binary
              image/png:
                schema:
                  type: string
                  format: binary
          400:
            content:
              application/json:
                schema: Error
        """

        instrument = (
            Instrument.query_records_accessible_by(
                self.current_user,
            )
            .filter(
                Instrument.id == instrument_id,
            )
            .first()
        )
        if instrument is None:
            return self.error(message=f"Missing instrument with id {instrument_id}")

        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        sourceID = self.get_query_argument('sourceID', None)
        status = self.get_query_argument('status', None)
        output_format = self.get_query_argument('output_format', 'csv')
        observation_start_date = self.get_query_argument('observationStartDate', None)
        observation_end_date = self.get_query_argument('observationEndDate', None)

        allocation_query = Allocation.query_records_accessible_by(
            self.current_user
        ).filter(Allocation.instrument_id == instrument_id)
        allocation_subquery = allocation_query.subquery()

        # get owned assignments
        followup_requests = FollowupRequest.query_records_accessible_by(
            self.current_user
        ).join(
            allocation_subquery,
            FollowupRequest.allocation_id == allocation_subquery.c.id,
        )

        if start_date:
            start_date = str(arrow.get(start_date.strip()).datetime)
            followup_requests = followup_requests.filter(
                FollowupRequest.created_at >= start_date
            )
        if end_date:
            end_date = str(arrow.get(end_date.strip()).datetime)
            followup_requests = followup_requests.filter(
                FollowupRequest.created_at <= end_date
            )
        if sourceID:
            obj_query = Obj.query_records_accessible_by(self.current_user).filter(
                Obj.id.contains(sourceID.strip())
            )
            obj_subquery = obj_query.subquery()
            followup_requests = followup_requests.join(
                obj_subquery, FollowupRequest.obj_id == obj_subquery.c.id
            )
        if status:
            followup_requests = followup_requests.filter(
                FollowupRequest.status.contains(status.strip())
            )
        if not observation_start_date:
            observation_start = Time.now()
        else:
            observation_start = Time(arrow.get(observation_start_date.strip()).datetime)
        if not observation_end_date:
            observation_end = Time.now() + TimeDelta(12 * u.hour)
        else:
            observation_end = Time(arrow.get(observation_end_date.strip()).datetime)

        followup_requests = followup_requests.options(
            joinedload(FollowupRequest.allocation).joinedload(Allocation.instrument),
            joinedload(FollowupRequest.allocation).joinedload(Allocation.group),
            joinedload(FollowupRequest.obj),
            joinedload(FollowupRequest.requester),
        ).all()

        if len(followup_requests) == 0:
            return self.error('Need at least one observation to schedule.')

        schedule = functools.partial(
            observation_schedule,
            followup_requests,
            instrument,
            observation_start=observation_start,
            observation_end=observation_end,
            output_format=output_format,
            figsize=(10, 8),
        )

        self.push_notification(
            'Schedule generation in progress. Download will start soon.'
        )
        rez = await IOLoop.current().run_in_executor(None, schedule)

        filename = rez["name"]
        data = io.BytesIO(rez["data"])

        await self.send_file(data, filename, output_type=output_format)
