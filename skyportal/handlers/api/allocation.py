import io

import astropy
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import sqlalchemy as sa
from astroplan.moon import moon_phase_angle
from marshmallow.exceptions import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token, permissions

from ...models import (
    Allocation,
    AllocationUser,
    FollowupRequest,
    Group,
    Instrument,
    User,
)
from ..base import BaseHandler


class AllocationHandler(BaseHandler):
    @auth_or_token
    def get(self, allocation_id=None):
        """
        ---
        single:
          tags:
            - allocations
          description: Retrieve an allocation
          parameters:
            - in: path
              name: allocation_id
              required: true
              schema:
                type: integer
          responses:
            200:
               content:
                application/json:
                  schema: SingleAllocation
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          tags:
            - allocations
          description: Retrieve all allocations
          parameters:
          - in: query
            name: instrument_id
            nullable: true
            schema:
              type: number
            description: Instrument ID to retrieve allocations for
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfAllocations
            400:
              content:
                application/json:
                  schema: Error
        """

        # get owned allocations

        with self.Session() as session:
            allocations = Allocation.select(self.current_user)

            if allocation_id is not None:
                try:
                    allocation_id = int(allocation_id)
                except ValueError:
                    return self.error("Allocation ID must be an integer.")
                allocations = Allocation.select(
                    self.current_user, options=[joinedload(Allocation.requests)]
                )

                allocations = allocations.where(Allocation.id == allocation_id)
                allocation = session.scalars(allocations).first()
                if allocation is None:
                    return self.error("Could not retrieve allocation.")

                allocation_data = allocation.to_dict()
                requests = []
                for request in allocation_data['requests']:
                    request_data = request.to_dict()
                    if request.requester is not None:
                        request_data['requester'] = request.requester.to_dict()
                    request_data['obj'] = request.obj.to_dict()
                    request_data['obj']['thumbnails'] = [
                        thumbnail.to_dict() for thumbnail in request.obj.thumbnails
                    ]
                    request_data['set_time_utc'] = request.set_time().iso
                    if isinstance(request_data['set_time_utc'], np.ma.MaskedArray):
                        request_data['set_time_utc'] = None
                    request_data['rise_time_utc'] = request.rise_time().iso
                    if isinstance(request_data['rise_time_utc'], np.ma.MaskedArray):
                        request_data['rise_time_utc'] = None
                    requests.append(request_data)
                allocation_data['requests'] = requests
                allocation_data[
                    'ephemeris'
                ] = allocation.instrument.telescope.ephemeris(astropy.time.Time.now())
                allocation_data['telescope'] = allocation.instrument.telescope.to_dict()
                return self.success(data=allocation_data)

            allocations = Allocation.select(self.current_user)
            instrument_id = self.get_query_argument('instrument_id', None)
            if instrument_id is not None:
                allocations = allocations.where(
                    Allocation.instrument_id == instrument_id
                )

            apitype = self.get_query_argument('apiType', None)
            if apitype is not None:
                if apitype == "api_classname":
                    instruments_subquery = (
                        sa.select(Instrument.id)
                        .where(Instrument.api_classname.isnot(None))
                        .distinct()
                        .subquery()
                    )

                    allocations = allocations.join(
                        instruments_subquery,
                        Allocation.instrument_id == instruments_subquery.c.id,
                    )
                elif apitype == "api_classname_obsplan":
                    instruments_subquery = (
                        sa.select(Instrument.id)
                        .where(Instrument.api_classname_obsplan.isnot(None))
                        .distinct()
                        .subquery()
                    )

                    allocations = allocations.join(
                        instruments_subquery,
                        Allocation.instrument_id == instruments_subquery.c.id,
                    )
                else:
                    return self.error(
                        f"apitype can only be api_classname or api_classname_obsplan, not {apitype}"
                    )

            allocations = session.scalars(allocations).unique().all()
            # order by allocation.instrument.telescope.name, then instrument.name, then pi
            allocations = sorted(
                allocations,
                key=lambda x: (
                    x.instrument.telescope.name,
                    x.instrument.name,
                    x.pi,
                ),
            )
            allocations = [
                {
                    **allocation.to_dict(),
                    'allocation_users': [
                        user.user.to_dict() for user in allocation.allocation_users
                    ],
                }
                for allocation in allocations
            ]
            return self.success(data=allocations)

    @permissions(['Manage allocations'])
    def post(self):
        """
        ---
        description: Post new allocation on a robotic instrument
        tags:
          - allocations
        requestBody:
          content:
            application/json:
              schema: AllocationNoID
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
                              description: New allocation ID
        """

        data = self.get_json()
        with self.Session() as session:
            allocation_admin_ids = data.pop('allocation_admin_ids', None)
            if allocation_admin_ids is not None:
                allocation_admins = session.scalars(
                    User.select(self.current_user).where(
                        User.id.in_(allocation_admin_ids)
                    )
                ).all()
            else:
                allocation_admins = []

            try:
                allocation = Allocation.__schema__().load(data=data)
            except ValidationError as e:
                return self.error(
                    f'Error parsing posted allocation: "{e.normalized_messages()}"'
                )

            group = session.scalars(
                Group.select(session.user_or_token).where(
                    Group.id == allocation.group_id
                )
            ).first()
            if group is None:
                return self.error(f'No group with specified ID: {allocation.group_id}')

            instrument = session.scalars(
                Instrument.select(session.user_or_token).where(
                    Instrument.id == allocation.instrument_id
                )
            ).first()
            if instrument is None:
                return self.error(
                    f'No group with specified ID: {allocation.instrument_id}'
                )

            session.add(allocation)

            for user in allocation_admins:
                session.merge(user)

            session.add_all(
                [
                    AllocationUser(allocation=allocation, user=user)
                    for user in allocation_admins
                ]
            )

            session.commit()
            self.push_all(action='skyportal/REFRESH_ALLOCATIONS')
            return self.success(data={"id": allocation.id})

    @permissions(['Manage allocations'])
    def put(self, allocation_id):
        """
        ---
        description: Update an allocation on a robotic instrument
        tags:
          - allocations
        parameters:
          - in: path
            name: allocation_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: AllocationNoID
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
            allocation = session.scalars(
                Allocation.select(session.user_or_token, mode="update").where(
                    Allocation.id == int(allocation_id)
                )
            ).first()
            if allocation is None:
                return self.error('No such allocation')

            data = self.get_json()
            data['id'] = allocation_id

            allocation_admin_ids = data.pop('allocation_admin_ids', [])

            if not isinstance(allocation_admin_ids, list):
                return self.error('allocation_admin_ids must be a list of user IDs')
            if not all(isinstance(x, int) for x in allocation_admin_ids):
                return self.error('allocation_admin_ids must be a list of user IDs')

            schema = Allocation.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )

            for k in data:
                setattr(allocation, k, data[k])

            users = session.scalars(
                User.select(self.current_user).where(User.id.in_(allocation_admin_ids))
            ).all()
            users_ids = [user.id for user in users]

            for au in allocation.allocation_users:
                if au.user_id not in users_ids:
                    session.delete(au)

            for user in users:
                if user.id not in [au.user_id for au in allocation.allocation_users]:
                    session.add(AllocationUser(allocation=allocation, user=user))

            session.commit()
            self.push_all(action='skyportal/REFRESH_ALLOCATIONS')
            return self.success()

    @permissions(['Manage allocations'])
    def delete(self, allocation_id):
        """
        ---
        description: Delete allocation.
        tags:
          - allocations
        parameters:
          - in: path
            name: allocation_id
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
            allocation = session.scalars(
                Allocation.select(session.user_or_token, mode="delete").where(
                    Allocation.id == int(allocation_id)
                )
            ).first()
            if allocation is None:
                return self.error('No such allocation')

            session.delete(allocation)
            session.commit()
            self.push_all(action='skyportal/REFRESH_ALLOCATIONS')
            return self.success()


class AllocationReportHandler(BaseHandler):
    @auth_or_token
    async def get(self, instrument_id):
        """
        ---
        tags:
          - allocations
        description: Produce a report on allocations for an instrument
        parameters:
          - in: path
            name: instrument_id
            required: true
            schema:
              type: integer
          - in: query
            name: output_format
            nullable: true
            schema:
              type: string
            description: |
              Output format for analysis. Can be png or pdf
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

        output_format = self.get_query_argument('output_format', 'pdf')
        if output_format not in ["pdf", "png"]:
            return self.error('output_format must be png or pdf')

        with self.Session() as session:
            # get owned allocations
            stmt = Allocation.select(session.user_or_token)
            stmt = stmt.where(Allocation.instrument_id == instrument_id)
            allocations = session.scalars(stmt).unique().all()

            if len(allocations) == 0:
                return self.error('Need at least one allocation for analysis')

            instrument = allocations[0].instrument

            labels = [a.proposal_id for a in allocations]
            values = [a.hours_allocated for a in allocations]

            def make_autopct(values, label="Hours"):
                def my_autopct(pct):
                    total = sum(values)
                    if np.isnan(pct):
                        val = 0
                    else:
                        val = int(round(pct * total / 100.0))
                    return f'{pct:.0f}%  ({val:d} {label})'

                return my_autopct

            matplotlib.use("Agg")
            fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4, figsize=(16, 6))
            ax1.pie(
                values,
                labels=labels,
                shadow=True,
                startangle=90,
                autopct=make_autopct(values, label="Hours"),
            )
            ax1.axis('equal')
            ax1.set_title('Time Allocated')

            values = [len(a.requests) for a in allocations]
            if sum(values) > 0:
                ax2.pie(
                    values,
                    labels=labels,
                    shadow=True,
                    startangle=90,
                    autopct=make_autopct(values, label="Requests"),
                )
                ax2.axis('equal')
                ax2.set_title('Requests Made')
            else:
                ax2.remove()

            values = []
            phases = []
            for a in allocations:
                stmt = (
                    FollowupRequest.select(session.user_or_token)
                    .where(FollowupRequest.allocation_id == a.id)
                    .where(FollowupRequest.status.contains('Complete'))
                )
                total_matches = session.execute(
                    sa.select(func.count()).select_from(stmt)
                ).scalar()
                values.append(total_matches)

                followup_requests = session.scalars(stmt).all()
                phase_angles = []
                for followup_request in followup_requests:
                    try:
                        status_split = followup_request.status.split(" ")[-1]
                        status_split = status_split.replace("_", ":").replace(" ", "T")
                        tt = astropy.time.Time(status_split, format='isot')
                        phase_angle = moon_phase_angle(tt)
                        phase_angles.append(phase_angle.value)
                    except Exception:
                        pass
                phases.append(phase_angles)

            if sum(values) > 0:
                ax3.pie(
                    values,
                    labels=labels,
                    shadow=True,
                    startangle=90,
                    autopct=make_autopct(values, label="Observations"),
                )
                ax3.axis('equal')
                ax3.set_title('Requests Completed')
            else:
                ax3.remove()

            bins = np.linspace(0, np.pi, 20)
            for ii, (label, phase_angles) in enumerate(zip(labels, phases)):
                hist, bin_edges = np.histogram(phase_angles, bins=bins)
                bin_centers = (bin_edges[1:] + bin_edges[:-1]) / 2.0
                hist = hist / np.sum(hist)
                ax4.step(bin_centers, hist, label=label)
            ax4.set_yscale('log')
            ax4.set_xlabel('Phase Angle')
            ax4.legend(loc='upper right')
            ax4.axis('equal')
            ax4.set_title('Moon Phase')

            buf = io.BytesIO()
            fig.savefig(buf, format=output_format)
            plt.close(fig)
            buf.seek(0)

            data = io.BytesIO(buf.read())
            filename = f"allocations_{instrument.name}.{output_format}"

            await self.send_file(data, filename, output_type=output_format)
