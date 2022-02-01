import numpy as np
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token, AccessError
from baselayer.app.model_util import recursive_to_dict
from ..base import BaseHandler
from ...models import (
    DBSession,
    ObservingRun,
    ClassicalAssignment,
    Obj,
    Instrument,
    Source,
)
from ...models.schema import ObservingRunPost, ObservingRunGetWithAssignments


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
        self.verify_and_commit()

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
            # These are all read=public, including Objs
            options = [
                joinedload(ObservingRun.assignments)
                .joinedload(ClassicalAssignment.obj)
                .joinedload(Obj.thumbnails),
                joinedload(ObservingRun.assignments).joinedload(
                    ClassicalAssignment.requester
                ),
                joinedload(ObservingRun.instrument).joinedload(Instrument.telescope),
            ]

            run = ObservingRun.get_if_accessible_by(
                run_id,
                self.current_user,
                mode="read",
                raise_if_none=True,
                options=options,
            )

            # order the assignments by ra
            assignments = sorted(run.assignments, key=lambda a: a.obj.ra)

            data = ObservingRunGetWithAssignments.dump(run)
            data["assignments"] = [a.to_dict() for a in assignments]

            for a in data["assignments"]:
                a['accessible_group_names'] = [
                    (s.group.nickname if s.group.nickname is not None else s.group.name)
                    for s in Source.query_records_accessible_by(
                        self.current_user, mode="read"
                    )
                    .filter(Source.obj_id == a["obj"].id)
                    .all()
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
            self.verify_and_commit()
            return self.success(data=data)

        runs = (
            ObservingRun.query_records_accessible_by(self.current_user, mode="read")
            .order_by(ObservingRun.calendar_date.asc())
            .all()
        )
        runs_list = []
        for run in runs:
            runs_list.append(run.to_dict())
            runs_list[-1]["run_end_utc"] = run.instrument.telescope.next_sunrise(
                run.calendar_noon
            ).isot

        self.verify_and_commit()
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

        try:
            orun = ObservingRun.get_if_accessible_by(
                run_id, self.current_user, mode="update", raise_if_none=True
            )
        except AccessError as e:
            return self.error(
                f"Only the owner of an observing run can modify the run. Original error: {e}"
            )

        try:
            new_params = ObservingRunPost.load(data, partial=True)
        except ValidationError as exc:
            return self.error(
                f"Invalid/missing parameters: {exc.normalized_messages()}"
            )

        for param in new_params:
            setattr(orun, param, new_params[param])

        DBSession().add(orun)
        self.verify_and_commit()

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

        try:
            run = ObservingRun.get_if_accessible_by(
                run_id, self.current_user, mode="delete", raise_if_none=True
            )
        except AccessError as e:
            return self.error(
                f"Only the owner of an observing run can delete the run. Original error: {e}"
            )

        DBSession().delete(run)
        self.verify_and_commit()

        self.push_all(action="skyportal/FETCH_OBSERVING_RUNS")
        return self.success()
