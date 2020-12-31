import numpy as np
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token, AccessError
from ..base import BaseHandler
from ...models import (
    DBSession,
    ObservingRun,
    ClassicalAssignment,
    Obj,
    Instrument,
    Source,
)
from ...schema import ObservingRunPost, ObservingRunGetWithAssignments


class ObservingRunHandler(BaseHandler):
    @permissions(["Upload data"])
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

        try:
            rund = ObservingRunPost.load(data)
        except ValidationError as exc:
            return self.error(
                f"Invalid/missing parameters: {exc.normalized_messages()}"
            )

        run = ObservingRun(**rund)
        run.owner_id = self.associated_user_object.id

        DBSession().add(run)
        self.finalize_transaction()

        self.push_all(action="skyportal/FETCH_OBSERVING_RUNS")
        return self.success(data={"id": run.id})

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
        if run_id is not None:
            run = (
                DBSession()
                .query(ObservingRun)
                .options(
                    joinedload(ObservingRun.assignments)
                    .joinedload(ClassicalAssignment.obj)
                    .joinedload(Obj.thumbnails),
                    joinedload(ObservingRun.assignments).joinedload(
                        ClassicalAssignment.requester
                    ),
                    joinedload(ObservingRun.instrument).joinedload(
                        Instrument.telescope
                    ),
                    joinedload(ObservingRun.assignments)
                    .joinedload(ClassicalAssignment.obj)
                    .joinedload(Obj.sources)
                    .joinedload(Source.group),
                )
                .filter(ObservingRun.id == run_id)
                .first()
            )

            if run is None:
                return self.error(
                    f"Could not load observing run {run_id}", data={"run_id": run_id}
                )

            # filter out the assignments of objects that are not visible to
            # the user
            assignments = []
            for a in run.assignments:
                try:
                    obj = Obj.get_if_readable_by(a.obj.id, self.current_user)
                except AccessError:
                    continue
                if obj is not None:
                    assignments.append(a)

            # order the assignments by ra
            assignments = sorted(run.assignments, key=lambda a: a.obj.ra)

            data = ObservingRunGetWithAssignments.dump(run)
            data["assignments"] = [a.to_dict() for a in assignments]

            gids = [
                g.id
                for g in self.current_user.accessible_groups
                if not g.single_user_group
            ]
            for a in data["assignments"]:
                a['accessible_group_names'] = [
                    (s.group.nickname if s.group.nickname is not None else s.group.name)
                    for s in a['obj'].sources
                    if s.group_id in gids
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

            # TODO: uncomment once API is refactored - this is currently commented
            # as this handler implements some changes to persistent records that
            # should not ever be flushed to the database

            # self.verify_permissions()
            return self.success(data=data)

        runs = ObservingRun.query.order_by(ObservingRun.calendar_date.asc()).all()
        runs_list = []
        for run in runs:
            runs_list.append(run.to_dict())
            runs_list[-1]["run_end_utc"] = run.instrument.telescope.next_sunrise(
                run.calendar_noon
            ).isot

        self.verify_permissions()
        return self.success(data=runs_list)

    @permissions(["Upload data"])
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
        is_superadmin = self.current_user.is_system_admin

        orun = ObservingRun.query.get(run_id)

        current_user_id = self.associated_user_object.id

        if orun.owner_id != current_user_id and not is_superadmin:
            return self.error("Only the owner of an observing run can modify the run.")
        try:
            new_params = ObservingRunPost.load(data, partial=True)
        except ValidationError as exc:
            return self.error(
                f"Invalid/missing parameters: {exc.normalized_messages()}"
            )

        for param in new_params:
            setattr(orun, param, new_params[param])

        DBSession().add(orun)
        self.finalize_transaction()

        self.push_all(action="skyportal/FETCH_OBSERVING_RUNS")
        return self.success()

    @permissions(["Upload data"])
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
        is_superadmin = self.current_user.is_system_admin

        run = ObservingRun.query.get(run_id)

        current_user_id = self.associated_user_object.id

        if run.owner_id != current_user_id and not is_superadmin:
            return self.error("Only the owner of an observing run can modify the run.")

        DBSession().query(ObservingRun).filter(ObservingRun.id == run_id).delete()
        self.finalize_transaction()

        self.push_all(action="skyportal/FETCH_OBSERVING_RUNS")
        return self.success()
