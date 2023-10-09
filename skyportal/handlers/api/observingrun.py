import numpy as np
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.model_util import recursive_to_dict
from baselayer.app.flow import Flow
from ..base import BaseHandler
from ...models import (
    ObservingRun,
    ClassicalAssignment,
    Obj,
    Instrument,
    Source,
    User,
)
from ...models.schema import ObservingRunPost, ObservingRunGetWithAssignments


def post_observing_run(data, user_id, session):
    """Post ObservingRun to database.
    data: dict
        Observing run dictionary
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    """

    user = session.query(User).get(user_id)

    try:
        rund = ObservingRunPost.load(data)
    except ValidationError as exc:
        raise ValidationError(
            f"Invalid/missing parameters: {exc.normalized_messages()}"
        )

    run = ObservingRun(**rund)
    run.owner_id = user.id

    session.add(run)
    session.commit()

    run.calculate_run_end_utc()
    session.commit()

    flow = Flow()
    flow.push('*', "skyportal/FETCH_OBSERVING_RUNS")

    return run.id


class ObservingRunHandler(BaseHandler):
    @permissions(["Manage observing runs"])
    def post(self):
        """
        ---
        description: Add a new observing run
        tags:
          - observing_runs
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

        with self.Session() as session:
            run_id = post_observing_run(data, self.associated_user_object.id, session)
            return self.success(data={"id": run_id})

    @auth_or_token
    def get(self, run_id=None):
        """
        ---
        single:
          description: Retrieve an observing run
          tags:
            - observing_runs
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
          description: Retrieve all observing runs
          tags:
            - observing_runs
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
        with self.Session() as session:
            if run_id is not None:
                # These are all read=public, including Objs
                options = [
                    joinedload(ObservingRun.assignments)
                    .joinedload(ClassicalAssignment.obj)
                    .joinedload(Obj.thumbnails),
                    joinedload(ObservingRun.assignments).joinedload(
                        ClassicalAssignment.requester
                    ),
                    joinedload(ObservingRun.instrument).joinedload(
                        Instrument.telescope
                    ),
                ]

                run = session.scalars(
                    ObservingRun.select(session.user_or_token, options=options).where(
                        ObservingRun.id == run_id
                    )
                ).first()
                if run is None:
                    return self.error(f'Cannot find ObservingRun with ID {run_id}')

                # order the assignments by ra
                assignments = sorted(run.assignments, key=lambda a: a.obj.ra)

                data = ObservingRunGetWithAssignments.dump(run)
                data["assignments"] = [a.to_dict() for a in assignments]

                for a in data["assignments"]:
                    a['accessible_group_names'] = [
                        (
                            s.group.nickname
                            if s.group.nickname is not None
                            else s.group.name
                        )
                        for s in session.scalars(
                            Source.select(session.user_or_token).where(
                                Source.obj_id == a["obj"].id
                            )
                        ).all()
                    ]
                    del a['obj'].sources
                    del a['obj'].users

                # vectorized calculation of ephemerides

                if len(data["assignments"]) > 0:
                    targets = [a['obj'].target for a in data["assignments"]]

                    rise_times = run.rise_time(targets).isot
                    set_times = run.set_time(targets).isot

                    for d, rt, st in zip(data["assignments"], rise_times, set_times):
                        d["rise_time_utc"] = rt if rt is not np.ma.masked else ''
                        d["set_time_utc"] = st if st is not np.ma.masked else ''

                data = recursive_to_dict(data)
                return self.success(data=data)

            runs = session.scalars(
                ObservingRun.select(session.user_or_token).order_by(
                    ObservingRun.calendar_date.asc()
                )
            ).all()

            # temporary, until we have migrated and called the handler once
            for run in runs:
                if run.run_end_utc is None:
                    run.calculate_run_end_utc()
                    session.commit()

            runs_list = [run.to_dict() for run in runs]

            return self.success(data=runs_list)

    @permissions(["Manage observing runs"])
    def put(self, run_id):
        """
        ---
        description: Update observing run
        tags:
          - observing_runs
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
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()
        run_id = int(run_id)

        with self.Session() as session:
            orun = session.scalars(
                ObservingRun.select(session.user_or_token, mode="update")
            ).first()
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
            session.commit()

            orun.calculate_run_end_utc()
            session.commit()

            self.push_all(action="skyportal/FETCH_OBSERVING_RUNS")
            return self.success()

    @auth_or_token
    def delete(self, run_id):
        """
        ---
        description: Delete an observing run
        tags:
          - observing_runs
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
        with self.Session() as session:
            orun = session.scalars(
                ObservingRun.select(session.user_or_token, mode="delete")
            ).first()
            if orun is None:
                return self.error(
                    "Only the owner of an observing run can delete the run."
                )

            session.delete(orun)
            session.commit()

            self.push_all(action="skyportal/FETCH_OBSERVING_RUNS")
            return self.success()
