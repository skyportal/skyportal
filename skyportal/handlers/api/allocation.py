from ..base import BaseHandler
from ...models import DBSession, Group, Allocation, Instrument
from baselayer.app.access import auth_or_token, permissions
from marshmallow.exceptions import ValidationError


class AllocationHandler(BaseHandler):
    @auth_or_token
    def get(self, allocation_id=None):
        """
        ---
        single:
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
          description: Retrieve all allocations
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
        allocations = (
            DBSession()
            .query(Allocation)
            .filter(
                Allocation.group_id.in_(
                    [g.id for g in self.current_user.accessible_groups]
                )
            )
        )

        if allocation_id is not None:
            try:
                allocation_id = int(allocation_id)
            except ValueError:
                return self.error("Allocation ID must be an integer.")

            allocations = allocations.filter(Allocation.id == allocation_id)

        allocations = allocations.all()

        if len(allocations) == 0 and allocation_id is not None:
            return self.error("Could not retrieve allocation.")

        out_json = Allocation.__schema__().dump(allocations, many=True)

        if allocation_id is not None:
            out_json = out_json[0]

        return self.success(data=out_json)

    @permissions(['System admin'])
    def post(self):
        """
        ---
        description: Post new allocation on a robotic instrument
        requestBody:
          content:
            application/json:
              schema: AllocationSchema
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
        try:
            allocation = Allocation.__schema__().load(data=data)
        except ValidationError as e:
            return self.error(
                f'Error parsing posted allocation: "{e.normalized_messages()}"'
            )

        group = Group.query.get(allocation.group_id)
        if group is None:
            return self.error(f'No group with specified ID: {allocation.group_id}')

        instrument = Instrument.query.get(allocation.instrument_id)
        if instrument is None:
            return self.error(f'No group with specified ID: {allocation.instrument_id}')

        DBSession().add(allocation)
        DBSession().commit()
        return self.success(data={"id": allocation.id})

    @permissions(['System admin'])
    def put(self, allocation_id):
        """
        ---
        description: Update an allocation on a robotic instrument
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
        allocation = Allocation.query.get(int(allocation_id))

        if allocation is None:
            return self.error('No such allocation')

        data = self.get_json()
        data['id'] = allocation_id

        schema = Allocation.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        DBSession().commit()
        return self.success()

    @permissions(['System admin'])
    def delete(self, allocation_id):
        """
        ---
        description: Delete allocation.
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
        allocation = Allocation.query.get(int(allocation_id))
        DBSession().delete(allocation)
        DBSession().commit()
        return self.success()
