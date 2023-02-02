import arrow
from datetime import datetime, timedelta
import healpy as hp
import jsonschema
from marshmallow.exceptions import ValidationError
import numpy as np
import io
from tornado.ioloop import IOLoop
import pandas as pd
import tempfile
import functools
import json
from scipy.stats import norm
import sqlalchemy as sa
from sqlalchemy import func

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.coordinates import EarthLocation
from astropy.time import Time, TimeDelta

from astroplan import Observer
from astroplan import FixedTarget
from astroplan import ObservingBlock
from astroplan.constraints import (
    Constraint,
    AltitudeConstraint,
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
from baselayer.app.flow import Flow
from ..base import BaseHandler
from ...models import (
    DefaultFollowupRequest,
    FollowupRequest,
    FollowupRequestUser,
    Instrument,
    ClassicalAssignment,
    Localization,
    ObservingRun,
    Obj,
    Group,
    User,
    Allocation,
    cosmo,
)

from sqlalchemy.orm import joinedload

from ...models.schema import AssignmentSchema, FollowupRequestPost

MAX_FOLLOWUP_REQUESTS = 1000


def post_assignment(data, session):
    """Post assignment to database.
    data: dict
        Assignment dictionary
    session: sqlalchemy.Session
        Database session for this transaction
    """

    try:
        assignment = ClassicalAssignment(**AssignmentSchema.load(data=data))
    except ValidationError as e:
        raise ValidationError(
            'Error parsing followup request: ' f'"{e.normalized_messages()}"'
        )

    run_id = assignment.run_id
    data['priority'] = assignment.priority.name
    run = session.scalars(
        ObservingRun.select(session.user_or_token).where(ObservingRun.id == run_id)
    ).first()
    if run is None:
        raise ValueError('Observing run is not accessible.')

    predecessor = session.scalars(
        ClassicalAssignment.select(session.user_or_token).where(
            ClassicalAssignment.obj_id == assignment.obj_id,
            ClassicalAssignment.run_id == run_id,
        )
    ).first()

    if predecessor is not None:
        raise ValueError('Object is already assigned to this run.')

    assignment = ClassicalAssignment(**data)

    if hasattr(session.user_or_token, 'created_by'):
        user_id = session.user_or_token.created_by.id
    else:
        user_id = session.user_or_token.id

    assignment.requester_id = user_id
    assignment.last_modified_by_id = user_id
    session.add(assignment)
    session.commit()

    flow = Flow()
    flow.push(
        '*',
        "skyportal/REFRESH_SOURCE",
        payload={"obj_key": assignment.obj.internal_key},
    )
    flow.push(
        '*',
        "skyportal/REFRESH_OBSERVING_RUN",
        payload={"run_id": assignment.run_id},
    )
    return assignment.id


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

        with self.Session() as session:

            # get owned assignments
            assignments = ClassicalAssignment.select(self.current_user)

            if assignment_id is not None:
                try:
                    assignment_id = int(assignment_id)
                except ValueError:
                    return self.error("Assignment ID must be an integer.")

                assignments = assignments.where(
                    ClassicalAssignment.id == assignment_id
                ).options(
                    joinedload(ClassicalAssignment.obj).joinedload(Obj.thumbnails),
                    joinedload(ClassicalAssignment.requester),
                    joinedload(ClassicalAssignment.obj),
                )

            assignments = session.scalars(assignments).unique().all()

            if len(assignments) == 0 and assignment_id is not None:
                return self.error(
                    "Could not retrieve assignment with ID {assignment_id}."
                )

            out_json = ClassicalAssignment.__schema__().dump(assignments, many=True)

            # calculate when the targets rise and set
            for json_obj, assignment in zip(out_json, assignments):
                json_obj['rise_time_utc'] = assignment.rise_time.isot
                json_obj['set_time_utc'] = assignment.set_time.isot
                json_obj['obj'] = assignment.obj
                json_obj['requester'] = assignment.requester

            if assignment_id is not None:
                out_json = out_json[0]

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

        with self.Session() as session:
            try:
                assignment_id = post_assignment(data, session)
            except ValidationError as e:
                return self.error(
                    'Error posting followup request: ' f'"{e.normalized_messages()}"'
                )
            except ValueError as e:
                return self.error('Error posting followup request: ' f'"{e.args[0]}"')
            except Exception as e:
                return self.error('Error posting followup request: ' f'"{str(e)}"')

            return self.success(data={"id": assignment_id})

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

        with self.Session() as session:
            assignment = session.scalars(
                ClassicalAssignment.select(self.current_user, mode="update").where(
                    ClassicalAssignment.id == int(assignment_id)
                )
            ).first()
            if assignment is None:
                return self.error(f'Could not find assigment with ID {assignment_id}.')

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

            if 'comment' in data:
                assignment.comment = data['comment']

            if 'status' in data:
                assignment.status = data['status']

            if 'priority' in data:
                assignment.priority = data['priority']

            if 'last_modified_by_id' in data:
                assignment.last_modified_by_id = data['last_modified_by_id']

            session.commit()

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

        with self.Session() as session:
            assignment = session.scalars(
                ClassicalAssignment.select(self.current_user, mode="update").where(
                    ClassicalAssignment.id == int(assignment_id)
                )
            ).first()
            if assignment is None:
                return self.error(f'Could not find assigment with ID {assignment_id}.')

            obj_key = assignment.obj.internal_key
            session.delete(assignment)
            session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": obj_key},
            )
            self.push_all(
                action="skyportal/REFRESH_OBSERVING_RUN",
                payload={"run_id": assignment.run_id},
            )
            return self.success()


def post_followup_request(data, session, refresh_source=True):
    """Post follow-up request to database.
    data: dict
        Follow-up request dictionary
    session: sqlalchemy.Session
        Database session for this transaction
    refresh_source : bool
        Refresh source upon post. Defaults to True.
    """

    stmt = Allocation.select(session.user_or_token).where(
        Allocation.id == data['allocation_id'],
    )
    allocation = session.scalars(stmt).first()
    if allocation is None:
        raise ValueError(f'Could not find allocation with ID {data["allocation_id"]}.')

    instrument = allocation.instrument
    if instrument is None:
        raise ValueError(f'Could not find instrument for allocation {allocation.id}.')

    if instrument.api_classname is None:
        raise ValueError('Instrument has no remote API.')

    if not instrument.api_class.implements()['submit']:
        raise ValueError('Cannot submit followup requests to this Instrument.')

    group_ids = data.pop('target_group_ids', [])
    stmt = Group.select(session.user_or_token).where(Group.id.in_(group_ids))
    target_groups = session.scalars(stmt).all()

    watcher_ids = data.pop('watcher_ids', None)
    if watcher_ids is not None:
        watchers = session.scalars(
            sa.select(User).where(User.id.in_(watcher_ids))
        ).all()
    else:
        watchers = []

    try:
        formSchema = instrument.api_class.custom_json_schema(
            instrument, session.user_or_token
        )
    except AttributeError:
        formSchema = instrument.api_class.form_json_schema

    # validate the payload
    jsonschema.validate(data['payload'], formSchema)

    followup_request = FollowupRequest.__schema__().load(data)
    followup_request.target_groups = target_groups
    followup_request.watchers = watchers
    session.add(followup_request)

    if refresh_source:
        session.commit()

        flow = Flow()
        flow.push(
            '*',
            "skyportal/REFRESH_SOURCE",
            payload={"obj_key": followup_request.obj.internal_key},
        )

    try:
        instrument.api_class.submit(
            followup_request, session, refresh_source=refresh_source
        )
    except Exception:
        followup_request.status = 'failed to submit'
        raise
    finally:
        if refresh_source:
            session.commit()
            flow.push(
                '*',
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": followup_request.obj.internal_key},
            )

    return followup_request.id


class FollowupRequestHandler(BaseHandler):
    @auth_or_token
    def get(self, followup_request_id=None):
        f"""
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
            name: instrumentID
            nullable: true
            schema:
              type: integer
            description: Instrument ID to filter on
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
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of followup requests to return per paginated request. Defaults to 100. Can be no larger than {MAX_FOLLOWUP_REQUESTS}.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for paginated query results. Defaults to 1
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
        instrumentID = self.get_query_argument('instrumentID', None)
        status = self.get_query_argument('status', None)
        page_number = self.get_query_argument("pageNumber", 1)
        n_per_page = self.get_query_argument("numPerPage", 100)

        try:
            page_number = int(page_number)
        except ValueError:
            return self.error("Invalid page number value.")
        try:
            n_per_page = int(n_per_page)
        except (ValueError, TypeError) as e:
            return self.error(f"Invalid numPerPage value: {str(e)}")

        if n_per_page > MAX_FOLLOWUP_REQUESTS:
            return self.error(
                f'numPerPage should be no larger than {MAX_FOLLOWUP_REQUESTS}.'
            )

        with self.Session() as session:

            # get owned assignments
            followup_requests = FollowupRequest.select(self.current_user)

            if followup_request_id is not None:
                try:
                    followup_request_id = int(followup_request_id)
                except ValueError:
                    return self.error("Assignment ID must be an integer.")

                followup_requests = followup_requests.where(
                    FollowupRequest.id == followup_request_id
                ).options(
                    joinedload(FollowupRequest.obj).joinedload(Obj.thumbnails),
                    joinedload(FollowupRequest.requester),
                    joinedload(FollowupRequest.obj),
                    joinedload(FollowupRequest.watchers),
                )
                followup_request = session.scalars(followup_requests).first()
                if followup_request is None:
                    return self.error("Could not retrieve followup request.")
                return self.success(data=followup_request)

            if start_date:
                start_date = str(arrow.get(start_date.strip()).datetime)
                followup_requests = followup_requests.where(
                    FollowupRequest.created_at >= start_date
                )
            if end_date:
                end_date = str(arrow.get(end_date.strip()).datetime)
                followup_requests = followup_requests.where(
                    FollowupRequest.created_at <= end_date
                )
            if sourceID:
                obj_query = Obj.select(self.current_user).where(
                    Obj.id.contains(sourceID.strip())
                )
                obj_subquery = obj_query.subquery()
                followup_requests = followup_requests.join(
                    obj_subquery, FollowupRequest.obj_id == obj_subquery.c.id
                )
            if instrumentID:
                # allocation query required as only way to reach
                # instrument_id is through allocation (as requests
                # are associated to allocations, not instruments)
                allocation_query = Allocation.select(self.current_user).where(
                    Allocation.instrument_id == instrumentID
                )
                allocation_subquery = allocation_query.subquery()
                followup_requests = followup_requests.join(
                    allocation_subquery,
                    FollowupRequest.allocation_id == allocation_subquery.c.id,
                )
            if status:
                followup_requests = followup_requests.where(
                    FollowupRequest.status.contains(status.strip())
                )

            followup_requests = followup_requests.options(
                joinedload(FollowupRequest.allocation).joinedload(
                    Allocation.instrument
                ),
                joinedload(FollowupRequest.allocation).joinedload(Allocation.group),
                joinedload(FollowupRequest.obj),
                joinedload(FollowupRequest.requester),
                joinedload(FollowupRequest.watchers),
            )

            count_stmt = sa.select(func.count()).select_from(followup_requests)
            total_matches = session.execute(count_stmt).scalar()
            if n_per_page is not None:
                followup_requests = (
                    followup_requests.distinct()
                    .limit(n_per_page)
                    .offset((page_number - 1) * n_per_page)
                )
            followup_requests = session.scalars(followup_requests).unique().all()

            info = {}
            info["followup_requests"] = [req.to_dict() for req in followup_requests]
            info["totalMatches"] = int(total_matches)
            return self.success(data=info)

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

        with self.Session() as session:

            data["requester_id"] = self.associated_user_object.id
            data["last_modified_by_id"] = self.associated_user_object.id
            data['allocation_id'] = int(data['allocation_id'])

            followup_request_id = post_followup_request(data, session)

            return self.success(data={"id": followup_request_id})

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

        with self.Session() as session:

            followup_request = session.scalars(
                FollowupRequest.select(session.user_or_token, mode="update").where(
                    FollowupRequest.id == request_id
                )
            ).first()
            if followup_request is None:
                return self.error(
                    message=f"Missing FollowUpRequest with id {request_id}"
                )

            data = self.get_json()

            if 'status' in data:
                # updating status does not require instrument API interaction
                for k in data:
                    setattr(followup_request, k, data[k])
            else:
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

                group_ids = data.pop('target_group_ids', None)
                if group_ids is not None:
                    stmt = Group.select(self.current_user).where(
                        Group.id.in_(group_ids)
                    )
                    target_groups = session.scalars(stmt).all()
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

                followup_request.instrument.api_class.update(followup_request, session)
            session.commit()

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

        with self.Session() as session:

            followup_request = session.scalars(
                FollowupRequest.select(session.user_or_token, mode="delete").where(
                    FollowupRequest.id == request_id
                )
            ).first()
            if followup_request is None:
                return self.error(
                    message=f"Missing FollowUpRequest with id {request_id}"
                )

            api = followup_request.instrument.api_class
            if not api.implements()['delete']:
                return self.error('Cannot delete requests on this instrument.')

            followup_request.last_modified_by_id = self.associated_user_object.id
            internal_key = followup_request.obj.internal_key

            api.delete(followup_request, session)
            session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": internal_key},
            )
            return self.success()


class HourAngleConstraint(Constraint):
    """
    Constrain the hour angle of a target.

    Parameters
    ----------
    min : float or `None`
        Minimum hour angle of the target. `None` indicates no limit.
    max : float or `None`
        Maximum hour angle of the target. `None` indicates no limit.
    """

    def __init__(self, min=-5.5, max=5.5):
        self.min = min
        self.max = max

    def compute_constraint(self, times, observer, targets):

        has = np.zeros((len(targets), len(times)))
        for ii, tt in enumerate(times):
            tt = Time(tt, format='jd', scale='utc', location=observer.location)
            lst = tt.sidereal_time('mean')
            has[:, ii] = [(lst - target.ra).hour for target in targets]

        if self.min is None and self.max is not None:
            mask = has <= self.max
        elif self.max is None and self.min is not None:
            mask = self.min <= has
        elif self.min is not None and self.max is not None:
            mask = (self.min <= has) & (has <= self.max)
        else:
            raise ValueError("No max and/or min specified in " "HourAngleConstraint.")
        return mask


class TargetOfOpportunityConstraint(Constraint):
    """
    Prioritize target of opportunity targets by giving them
    higher weights at earlier times.

    Parameters
    ----------
    toos : List[bool]
        List indicating whether targets are ToOs or not.
    tau : `~astropy.units.Quantity`
        Exponential decay constant for normalization (in days).
        Defaults to 1 hour.
    """

    def __init__(self, tau=1 / 24 * u.day, toos=None):
        self.tau = tau
        self.toos = toos

    def compute_constraint(self, times, observer, targets):
        tt = times - times[0]
        exp_func = np.exp(-tt / self.tau)
        exp_func = exp_func / np.max(exp_func)

        reward_function = np.ones((len(targets), len(times)))
        for ii, too in enumerate(self.toos):
            if too:
                reward_function[ii, :] = exp_func

        return reward_function


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

    blocks = []
    toos = []

    # FIXME: account for different instrument readout times
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

        if "too" in payload:
            too = payload["too"] in ["Y", "Yes", "True", "t", "true", "1", True, 1]
        else:
            too = False

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
                    'exposure_time': exposure_time,
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
                    'exposure_time': exposure_time,
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

            if too:
                toos.append(True)
            else:
                toos.append(False)

    global_constraints = [
        AirmassConstraint(max=2.50, boolean_constraint=False),
        AltitudeConstraint(20 * u.deg, 90 * u.deg),
        AtNightConstraint.twilight_civil(),
        HourAngleConstraint(min=-5.5, max=5.5),
        MoonSeparationConstraint(min=10.0 * u.deg),
        TargetOfOpportunityConstraint(toos=toos),
    ]

    # Initialize a transitioner object with the slew rate and/or the
    # duration of other transitions (e.g. filter changes)

    # FIXME: account for different telescope slew rates
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
            exposure_time = int(block["configuration"]["exposure_time"].value)

            obs_start = Time(block["start time (UTC)"], format='iso')
            obs_end = Time(block["end time (UTC)"], format='iso')

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

        with self.Session() as session:

            instrument = session.scalars(
                Instrument.select(self.current_user,).where(
                    Instrument.id == instrument_id,
                )
            ).first()
            if instrument is None:
                return self.error(message=f"Missing instrument with id {instrument_id}")

            start_date = self.get_query_argument('startDate', None)
            end_date = self.get_query_argument('endDate', None)
            sourceID = self.get_query_argument('sourceID', None)
            status = self.get_query_argument('status', None)
            output_format = self.get_query_argument('output_format', 'csv')
            observation_start_date = self.get_query_argument(
                'observationStartDate', None
            )
            observation_end_date = self.get_query_argument('observationEndDate', None)

            allocation_query = Allocation.select(self.current_user).where(
                Allocation.instrument_id == instrument_id
            )
            allocation_subquery = allocation_query.subquery()

            # get owned assignments
            followup_requests = FollowupRequest.select(self.current_user).join(
                allocation_subquery,
                FollowupRequest.allocation_id == allocation_subquery.c.id,
            )

            if start_date:
                start_date = str(arrow.get(start_date.strip()).datetime)
                followup_requests = followup_requests.where(
                    FollowupRequest.created_at >= start_date
                )
            if end_date:
                end_date = str(arrow.get(end_date.strip()).datetime)
                followup_requests = followup_requests.where(
                    FollowupRequest.created_at <= end_date
                )
            if sourceID:
                obj_query = Obj.select(self.current_user).where(
                    Obj.id.contains(sourceID.strip())
                )
                obj_subquery = obj_query.subquery()
                followup_requests = followup_requests.join(
                    obj_subquery, FollowupRequest.obj_id == obj_subquery.c.id
                )
            if status:
                followup_requests = followup_requests.where(
                    FollowupRequest.status.contains(status.strip())
                )
            if not observation_start_date:
                observation_start = Time.now()
            else:
                observation_start = Time(
                    arrow.get(observation_start_date.strip()).datetime
                )
            if not observation_end_date:
                observation_end = Time.now() + TimeDelta(12 * u.hour)
            else:
                observation_end = Time(arrow.get(observation_end_date.strip()).datetime)

            followup_requests = followup_requests.options(
                joinedload(FollowupRequest.allocation).joinedload(
                    Allocation.instrument
                ),
                joinedload(FollowupRequest.allocation).joinedload(Allocation.group),
                joinedload(FollowupRequest.obj),
                joinedload(FollowupRequest.requester),
            )

            followup_requests = session.scalars(followup_requests).unique().all()
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


class FollowupRequestPrioritizationHandler(BaseHandler):
    @auth_or_token
    async def put(self):
        """
        ---
        description: |
          Reprioritize followup requests schedule automatically based on
          either magnitude or location within skymap.
        tags:
            - followup_requests
        parameters:
        - in: body
          name: requestIds
          schema:
            type: list of integers
          description: List of follow-up request IDs
        - in: body
          name: priorityType
          schema:
            type: string
          description: Priority source. Must be either localization or magnitude. Defaults to magnitude.
        - in: body
          name: magnitudeOrdering
          schema:
            type: string
          description: Ordering for brightness based prioritization. Must be either ascending (brightest first) or descending (faintest first). Defaults to ascending.
        - in: body
          name: localizationId
          schema:
            type: integer
          description: Filter by localization ID
        - in: body
          name: minimumPriority
          schema:
            type: string
          description: Minimum priority for the instrument. Defaults to 1.
        - in: body
          name: maximumPriority
          schema:
            type: string
          description: Maximum priority for the instrument. Defaults to 5.
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
        priority_type = data.get('priorityType', 'magnitude')
        magnitude_ordering = data.get('magnitudeOrdering', 'ascending')
        localization_id = data.get('localizationId', None)
        request_ids = data.get('requestIds', None)
        minimum_priority = data.get('minimumPriority', 1)
        maximum_priority = data.get('maximumPriority', 5)

        if request_ids is None:
            return self.error('requestIds is required')

        if priority_type not in ["magnitude", "localization"]:
            return self.error('priority_type must be either magnitude or localization')

        if magnitude_ordering not in ["ascending", "descending"]:
            return self.error(
                'magnitude_ordering must be either ascending or descending'
            )

        with self.Session() as session:

            followup_requests = []
            for request_id in request_ids:
                # get owned assignments
                followup_request = session.scalars(
                    FollowupRequest.select(self.current_user, mode="update")
                    .options(joinedload(FollowupRequest.obj).joinedload(Obj.photstats))
                    .where(FollowupRequest.id == request_id)
                ).first()
                if followup_request is None:
                    return self.error(
                        message=f"Missing FollowUpRequest with id {request_id}"
                    )
                followup_requests.append(followup_request)

            if len(followup_requests) == 0:
                return self.error('Need at least one observation to modify.')

            if priority_type == "localization":
                if localization_id is None:
                    return self.error(
                        'localizationId is required if priorityType is localization'
                    )

                localization = session.scalars(
                    Localization.select(self.current_user).where(
                        Localization.id == localization_id,
                    )
                ).first()
                if localization is None:
                    return self.error(
                        message=f"Missing localization with id {localization_id}"
                    )

                ras = np.array(
                    [followup_request.obj.ra for followup_request in followup_requests]
                )
                decs = np.array(
                    [followup_request.obj.dec for followup_request in followup_requests]
                )
                dists = np.array(
                    [
                        cosmo.luminosity_distance(followup_request.obj.redshift).value
                        if followup_request.obj.redshift is not None
                        else -1
                        for followup_request in followup_requests
                    ]
                )

                tab = localization.flat
                ipix = hp.ang2pix(Localization.nside, ras, decs, lonlat=True)
                if localization.is_3d:
                    prob, distmu, distsigma, distnorm = tab
                    if not all([dist > 0 for dist in dists]):
                        weights = prob[ipix]
                    else:
                        weights = prob[ipix] * (
                            distnorm[ipix]
                            * norm(distmu[ipix], distsigma[ipix]).pdf(dists)
                        )
                else:
                    (prob,) = tab
                    weights = prob[ipix]

            elif priority_type == "magnitude":
                mags = np.array(
                    [
                        followup_request.obj.photstats[0].peak_mag_global
                        if followup_request.obj.photstats[0].peak_mag_global is not None
                        else 99
                        for followup_request in followup_requests
                    ]
                )
                if magnitude_ordering == "descending":
                    weights = mags - np.min(mags)
                else:
                    weights = -(mags - np.min(mags))
            if len(weights) > 1:
                weights = (weights - np.min(weights)) / (
                    np.max(weights) - np.min(weights)
                )
            else:
                weights = weights / np.max(weights)

            priorities = [
                int(
                    np.round(
                        weight * (maximum_priority - minimum_priority)
                        + minimum_priority
                    )
                )
                for weight in weights
            ]

            for followup_request, priority in zip(followup_requests, priorities):
                api = followup_request.instrument.api_class
                if not api.implements()['update']:
                    return self.error('Cannot update requests on this instrument.')
                payload = followup_request.payload
                payload["priority"] = priority
                session.query(FollowupRequest).filter(
                    FollowupRequest.id == request_id
                ).update({'payload': payload})
                session.commit()

                followup_request.payload = payload
                followup_request.instrument.api_class.update(followup_request, session)

            flow = Flow()
            flow.push(
                '*',
                "skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )

            return self.success()


class DefaultFollowupRequestHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Create default follow-up request.
        tags:
          - default_followup_request
        requestBody:
          content:
            application/json:
              schema: DefaultFollowupRequestPost
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
                              description: New default follow-up request ID
        """
        data = self.get_json()

        with self.Session() as session:
            target_group_ids = data.pop('target_group_ids', [])
            stmt = Group.select(self.current_user).where(Group.id.in_(target_group_ids))
            target_groups = session.scalars(stmt).all()

            stmt = Allocation.select(session.user_or_token).where(
                Allocation.id == data['allocation_id'],
            )
            allocation = session.scalars(stmt).first()
            if allocation is None:
                return self.error(
                    f"Cannot access allocation with ID: {data['allocation_id']}",
                    status=403,
                )

            instrument = allocation.instrument
            if instrument.api_classname is None:
                return self.error('Instrument has no remote API.', status=403)

            try:
                formSchema = instrument.api_class.custom_json_schema(
                    instrument, self.current_user
                )
            except AttributeError:
                formSchema = instrument.api_class.form_json_schema

            payload = data['payload']
            if "start_date" in payload:
                return self.error('Cannot have start_date in the payload')
            else:
                payload['start_date'] = str(datetime.utcnow())

            if "end_date" in payload:
                return self.error('Cannot have end_date in the payload')
            else:
                payload['end_date'] = str(datetime.utcnow() + timedelta(days=1))

            # validate the payload
            try:
                jsonschema.validate(payload, formSchema)
            except jsonschema.exceptions.ValidationError as e:
                return self.error(f'Payload failed to validate: {e}', status=403)

            if "source_filter" in data:
                if not isinstance(data["source_filter"], dict):
                    try:
                        data["source_filter"] = data["source_filter"].replace("'", '"')
                        data["source_filter"] = json.loads(data["source_filter"])
                    except json.decoder.JSONDecodeError:
                        return self.error(
                            'Incorrect format for source_filter. Must be a json string.'
                        )

            default_followup_request = DefaultFollowupRequest.__schema__().load(data)
            default_followup_request.target_groups = target_groups

            session.add(default_followup_request)
            session.commit()

            self.push_all(action="skyportal/REFRESH_DEFAULT_FOLLOWUP_REQUESTS")
            return self.success(data={"id": default_followup_request.id})

    @auth_or_token
    def get(self, default_followup_request_id=None):
        """
        ---
        single:
          description: Retrieve a single default follow-up request
          tags:
            - default_followup_requests
          parameters:
            - in: path
              name: default_followup_request_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleDefaultFollowupRequest
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all default follow-up requests
          tags:
            - filters
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfDefaultFollowupRequests
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:
            if default_followup_request_id is not None:
                default_followup_request = session.scalars(
                    DefaultFollowupRequest.select(
                        session.user_or_token,
                        mode="update",
                        options=[joinedload(DefaultFollowupRequest.allocation)],
                    ).where(DefaultFollowupRequest.id == default_followup_request_id)
                ).first()
                if default_followup_request is None:
                    return self.error(
                        f'Cannot find DefaultFollowupRequestRequest with ID {default_followup_request_id}'
                    )
                return self.success(data=default_followup_request)

            default_followup_requests = (
                session.scalars(
                    DefaultFollowupRequest.select(
                        session.user_or_token,
                        options=[joinedload(DefaultFollowupRequest.allocation)],
                    )
                )
                .unique()
                .all()
            )

            default_followup_request_data = []
            for request in default_followup_requests:
                default_followup_request_data.append(
                    {
                        **request.to_dict(),
                        'allocation': request.allocation.to_dict(),
                    }
                )

            return self.success(data=default_followup_request_data)

    @auth_or_token
    def delete(self, default_followup_request_id):
        """
        ---
        description: Delete a default follow-up request
        tags:
          - filters
        parameters:
          - in: path
            name: default_followup_request_id
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

            stmt = DefaultFollowupRequest.select(
                session.user_or_token, mode="delete"
            ).where(DefaultFollowupRequest.id == default_followup_request_id)
            default_followup_request = session.scalars(stmt).first()

            if default_followup_request is None:
                return self.error(
                    f'Default follow-up request with ID {default_followup_request_id} is not available.'
                )

            session.delete(default_followup_request)
            session.commit()
            self.push_all(action="skyportal/REFRESH_DEFAULT_FOLLOWUP_REQUESTS")
            return self.success()


class FollowupRequestWatcherHandler(BaseHandler):
    @auth_or_token
    def post(self, followup_request_id):
        """
        ---
        description: Add follow-up request to watch list
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
                  schema: Success
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:

            # get owned assignments
            followup_requests = FollowupRequest.select(self.current_user)

            try:
                followup_request_id = int(followup_request_id)
            except ValueError:
                return self.error("Assignment ID must be an integer.")

            followup_requests = followup_requests.where(
                FollowupRequest.id == followup_request_id
            ).options(
                joinedload(FollowupRequest.watchers),
            )
            followup_request = session.scalars(followup_requests).first()
            if followup_request is None:
                return self.error("Could not retrieve followup request.")

            watchers = followup_request.watchers
            if any([watcher.id == self.current_user.id for watcher in watchers]):
                return self.error("User already watching this request")

            watcher = FollowupRequestUser(
                user_id=self.current_user.id, followuprequest_id=followup_request_id
            )
            session.add(watcher)
            session.commit()

            flow = Flow()
            flow.push(
                user_id=self.current_user.id,
                action_type="skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )
            flow.push(
                user_id=self.current_user.id,
                action_type="skyportal/REFRESH_SOURCE",
                payload={"obj_key": followup_request.obj.internal_key},
            )

            return self.success()

    @auth_or_token
    def delete(self, followup_request_id):
        """
        ---
        description: Delete follow-up request from watch list
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
                  schema: Success
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:

            # get owned assignments
            followup_requests = FollowupRequest.select(self.current_user)

            try:
                followup_request_id = int(followup_request_id)
            except ValueError:
                return self.error("Assignment ID must be an integer.")

            followup_requests = followup_requests.where(
                FollowupRequest.id == followup_request_id
            ).options(
                joinedload(FollowupRequest.watchers),
            )
            followup_request = session.scalars(followup_requests).first()
            if followup_request is None:
                return self.error("Could not retrieve followup request.")

            watcher = session.scalars(
                FollowupRequestUser.select(self.current_user, mode="delete").where(
                    FollowupRequestUser.user_id == self.current_user.id,
                    FollowupRequestUser.followuprequest_id == followup_request_id,
                )
            ).first()
            if watcher is None:
                return self.error(
                    f"The user {self.current_user.id} is not watching request {followup_request_id}."
                )

            session.delete(watcher)
            session.commit()

            flow = Flow()
            flow.push(
                user_id=self.current_user.id,
                action_type="skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )
            flow.push(
                user_id=self.current_user.id,
                action_type="skyportal/REFRESH_SOURCE",
                payload={"obj_key": followup_request.obj.internal_key},
            )

            return self.success()
