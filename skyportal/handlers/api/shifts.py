import numpy as np
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token, AccessError
from baselayer.app.model_util import recursive_to_dict
from ..base import BaseHandler
from ...models import (
    DBSession,
    Shifts,
    User,
)
from ...models.schema import ShiftPost, ShiftsGetWithAssignments


class ObservingRunHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: Add a new shift
        tags:
          - shift
        requestBody:
          content:
            application/json:
              schema: ShiftPost
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
                              description: New Shift
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()

        try:
            shiftd = ShiftPost.load(data)
        except ValidationError as exc:
            return self.error(
                f"Invalid/missing parameters: {exc.normalized_messages()}"
            )

        shift = Shift(**shiftd)
        shift.user_id = self.user_id

        DBSession().add(shift)
        self.verify_and_commit()

        self.push_all(action="skyportal/FETCH_SHIFTS")
        return self.success(data={"id": shift.id})

    @auth_or_token
    def get(self, user_id=None, start_shift=None):
        """
        ---
        single:
          description: Retrieve shifts
          tags:
            - shift
          parameters:
            - in: path
              name: user_id
              required: false
              schema:
                type: integer
              name: start_shift
              required: false
              schema:
                type: datetime
          responses:
            200:
              content:
                application/json:
                  schema: ShiftsGetWithAssignments
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all shifts
          tags:
            - shifts
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfShifts
            400:
              content:
                application/json:
                  schema: Error
        """
        if user_id is not None:
            options = [
                joinedload(Shift.assignments)
                .joinedload(ClassicalAssignment.obj)
                joinedload(Shift.assignments).joinedload(
                    ClassicalAssignment.requester
                ),
            ]

            if start_shift is not None:
              shifts = Shift.get_if_accessible_by(
                  user_id,
                  start_shift,
                  self.current_user,
                  mode="read",
                  raise_if_none=True,
                  options=options,
              )

            else:
              shifts = Shift.get_if_accessible_by(
                  user_id,
                  self.current_user,
                  mode="read",
                  raise_if_none=True,
                  options=options,
              )

            # order the assignments by earliest shift
            assignments = sorted(shifts.assignments, key=lambda a: a.obj.start_shift)

            data = ShiftsGetWithAssignments.dump(shifts)
            data["assignments"] = [a.to_dict() for a in assignments]

            data = recursive_to_dict(data)
            self.verify_and_commit()
            return self.success(data=data)

        shifts = (
            Shift.query_records_accessible_by(self.current_user, mode="read")
            .order_by(Shift.shift_start.asc())
            .all()
        )
        shifts_list = []
        for shift in shifts:
            shifts_list.append(shift.to_dict())

        self.verify_and_commit()
        return self.success(data=shifts_list)

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
