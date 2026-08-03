import numpy as np
import sqlalchemy as sa
from astropy.utils.masked import MaskedNDArray
from marshmallow.exceptions import ValidationError
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.flow import Flow
from baselayer.app.model_util import recursive_to_dict
from skyportal.log import make_log

from ...models import (
    ClassicalAssignment,
    Instrument,
    Obj,
    ObservingRun,
    Source,
    User,
)
from ...models.schema import ObservingRunGetWithAssignments, ObservingRunPost
from ...utils.naive_datetime import utcnow_naive
from ..base import BaseHandler

log = make_log("api/observing_run")


async def post_observing_run(data, user_id, session):
    """Post ObservingRun to database.
    data: dict
        Observing run dictionary
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.ext.asyncio.AsyncSession
        Async database session for this transaction
    """

    user = await session.get(User, user_id)

    try:
        rund = ObservingRunPost.load(data)
    except ValidationError as exc:
        raise ValidationError(
            f"Invalid/missing parameters: {exc.normalized_messages()}"
        )

    run = ObservingRun(**rund)
    run.owner_id = user.id

    session.add(run)
    await session.commit()

    # reload with instrument/telescope eagerly so calculate_run_end_utc()
    # (which traverses run.instrument.telescope.observer) doesn't lazy-load
    # under the async session.
    run = await session.scalar(
        sa.select(ObservingRun)
        .options(
            selectinload(ObservingRun.instrument).selectinload(Instrument.telescope)
        )
        .where(ObservingRun.id == run.id)
    )
    run.calculate_run_end_utc()
    await session.commit()

    flow = Flow()
    flow.push("*", "skyportal/FETCH_OBSERVING_RUNS")

    return run.id


class ObservingRunHandler(BaseHandler):
    @permissions(["Manage observing runs"])
    async def post(self):
        """
        ---
        summary: Create an observing run
        description: Add a new observing run
        tags:
          - observing runs
        requestBody:
          content:
            application/json:
              schema: ObservingRunPost
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
                              description: New Observing Run ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()

        async with self.AsyncSession() as session:
            run_id = await post_observing_run(
                data, self.associated_user_object.id, session
            )
            return self.success(data={"id": run_id})

    @auth_or_token
    async def get(self, run_id: int | None = None):
        """
        ---
        single:
          summary: Get an observing run
          description: Retrieve an observing run
          tags:
            - observing runs
          parameters:
            - in: path
              name: run_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleObservingRunGetWithAssignments
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Get all observing runs
          description: Retrieve all observing runs
          tags:
            - observing runs
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfObservingRuns
            400:
              content:
                application/json:
                  schema: Error
        """
        run_id = int(run_id) if run_id is not None else None
        async with self.AsyncSession() as session:
            if run_id is not None:
                # These are all read=public, including Objs. selectinload
                # composes cleanly under async.
                options = [
                    selectinload(ObservingRun.assignments)
                    .selectinload(ClassicalAssignment.obj)
                    .selectinload(Obj.thumbnails),
                    selectinload(ObservingRun.assignments).selectinload(
                        ClassicalAssignment.requester
                    ),
                    selectinload(ObservingRun.instrument).selectinload(
                        Instrument.telescope
                    ),
                ]

                run = await session.scalar(
                    ObservingRun.select(session.user_or_token, options=options).where(
                        ObservingRun.id == run_id
                    )
                )
                if run is None:
                    return self.error(f"Cannot find ObservingRun with ID {run_id}")

                # order the assignments by ra
                assignments = sorted(run.assignments, key=lambda a: a.obj.ra)

                data = ObservingRunGetWithAssignments.dump(run)
                data["assignments"] = [a.to_dict() for a in assignments]

                for a in data["assignments"]:
                    sources_result = await session.scalars(
                        Source.select(session.user_or_token)
                        .options(selectinload(Source.group))
                        .where(Source.obj_id == a["obj"].id)
                    )
                    a["accessible_group_names"] = [
                        (
                            s.group.nickname
                            if s.group.nickname is not None
                            else s.group.name
                        )
                        for s in sources_result.all()
                    ]
                    del a["obj"].sources
                    del a["obj"].users

                # vectorized calculation of ephemerides

                if len(data["assignments"]) > 0:
                    targets = [a["obj"].target for a in data["assignments"]]

                    rise_times = run.rise_time(targets).isot
                    set_times = run.set_time(targets).isot

                    for d, rt, st in zip(data["assignments"], rise_times, set_times):
                        # we can an attribute error in the case where rt and st are not arrays
                        # this can happen if the observing run's date is missing or incorrect
                        # in the case of unit tests for example, or a "dubious" year for time-based packages
                        # (which is often anything before 1900, or after 2100)
                        try:
                            d["rise_time_utc"] = (
                                rt.item()  # 0-dimensional array (basically a scalar)
                                if not (
                                    isinstance(
                                        rt, np.ma.core.MaskedArray | MaskedNDArray
                                    )
                                    and rt.mask.any()
                                )  # check that the value isn't masked (not rising at date)
                                else ""
                            )
                        except AttributeError:
                            d["rise_time_utc"] = ""
                        try:
                            d["set_time_utc"] = (
                                st.item()
                                if not (
                                    isinstance(
                                        st, np.ma.core.MaskedArray | MaskedNDArray
                                    )
                                    and st.mask.any()
                                )  # check that the value isn't masked (not setting at date)
                                else ""
                            )
                        except AttributeError:
                            d["set_time_utc"] = ""

                data = recursive_to_dict(data)
                return self.success(data=data)

            result = await session.scalars(
                ObservingRun.select(session.user_or_token)
                .options(
                    selectinload(ObservingRun.instrument).selectinload(
                        Instrument.telescope
                    )
                )
                .order_by(ObservingRun.calendar_date.asc())
            )
            runs = result.all()

            # temporary, until we have migrated and called the handler once
            try:
                updated = False
                for run in runs:
                    if run.run_end_utc is None:
                        run.calculate_run_end_utc()
                        updated = True
                if updated:
                    await session.commit()
            except Exception as e:
                log.error(f"Error calculating run_end_utc: {e}")

            runs_list = [run.to_dict() for run in runs]

            return self.success(data=runs_list)

    @permissions(["Manage observing runs"])
    async def put(self, run_id: int):
        """
        ---
        summary: Update an observing run
        description: Update observing run
        tags:
          - observing runs
        parameters:
          - in: path
            name: run_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: ObservingRunPost
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
                          $ref: '#/components/schemas/ObservingRun'
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()
        run_id = int(run_id)

        async with self.AsyncSession() as session:
            orun = await session.scalar(
                ObservingRun.select(session.user_or_token, mode="update").where(
                    ObservingRun.id == run_id
                )
            )
            if orun is None:
                return self.error(
                    "Only the owner of an observing run can modify the run."
                )

            try:
                new_params = ObservingRunPost.load(data, partial=True)
            except ValidationError as exc:
                return self.error(
                    f"Invalid/missing parameters: {exc.normalized_messages()}"
                )

            for param in new_params:
                setattr(orun, param, new_params[param])

            session.add(orun)
            await session.commit()

            # Reload with instrument/telescope eager so calculate_run_end_utc
            # (which traverses orun.instrument.telescope.observer) doesn't
            # trigger a lazy load under the async session.
            orun = await session.scalar(
                sa.select(ObservingRun)
                .options(
                    selectinload(ObservingRun.instrument).selectinload(
                        Instrument.telescope
                    )
                )
                .where(ObservingRun.id == run_id)
            )
            orun.calculate_run_end_utc()
            await session.commit()

            self.push_all(action="skyportal/FETCH_OBSERVING_RUNS")
            return self.success()

    @auth_or_token
    async def delete(self, run_id: int):
        """
        ---
        summary: Delete an observing run
        description: Delete an observing run
        tags:
          - observing runs
        parameters:
          - in: path
            name: run_id
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
        run_id = int(run_id)
        async with self.AsyncSession() as session:
            orun = await session.scalar(
                ObservingRun.select(session.user_or_token, mode="delete")
                .options(selectinload(ObservingRun.assignments))
                .where(ObservingRun.id == run_id)
            )
            if orun is None:
                return self.error(
                    "Only the owner of an observing run can delete the run."
                )

            # check if any assignments are associated with this run
            assignments = []
            if orun.assignments is not None:
                assignments = orun.assignments

            # if any assignments have a status like completed or pending, we should not delete the run
            # and instead return an error
            for assignment in assignments:
                if assignment.status in ["complete", "pending"]:
                    return self.error(
                        "Cannot delete an observing run with assignments that are completed or pending. Mark these targets as unobserved first."
                    )

            # don't allow deleting past runs, unless they have no assignments
            if orun.run_end_utc < utcnow_naive() and len(assignments) > 0:
                return self.error(
                    "Cannot delete an observing run that has ended and had targets assigned to it."
                )

            # delete the assignments associated with this run
            for assignment in assignments:
                await session.delete(assignment)
            await session.delete(orun)
            await session.commit()

            self.push_all(action="skyportal/FETCH_OBSERVING_RUNS")
            return self.success()


class ObservingRunBulkEditHandler(BaseHandler):
    @auth_or_token
    async def put(self, run_id: int):
        """
        ---
        summary: Bulk update observing run assignments
        description: Update observing run assignments in bulk
        tags:
          - observing runs
        parameters:
          - in: path
            name: run_id
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

        data = self.get_json()
        run_id = int(run_id)

        current_status = data.get("current_status")
        if current_status is None:
            return self.error("Require current status to filter")

        new_status = data.get("new_status")
        if new_status is None:
            return self.error("Require new status to apply")

        async with self.AsyncSession() as session:
            options = [selectinload(ObservingRun.assignments)]

            run = await session.scalar(
                ObservingRun.select(session.user_or_token, options=options).where(
                    ObservingRun.id == run_id
                )
            )
            if run is None:
                return self.error(f"Cannot find ObservingRun with ID {run_id}")

            assignments = run.assignments
            for a in assignments:
                assignment = await session.scalar(
                    ClassicalAssignment.select(
                        session.user_or_token, mode="update"
                    ).where(ClassicalAssignment.id == int(a.id))
                )
                if assignment is None:
                    return self.error(f"Could not find assigment with ID {a.id}.")
                if assignment.status == current_status:
                    assignment.status = new_status

            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_OBSERVING_RUN",
                payload={"run_id": run_id},
            )

            return self.success()
