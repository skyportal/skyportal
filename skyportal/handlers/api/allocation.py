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
        allocations = Allocation.query_records_accessible_by(self.current_user)

        if allocation_id is not None:
            try:
                allocation_id = int(allocation_id)
            except ValueError:
                return self.error("Allocation ID must be an integer.")
            allocations = allocations.filter(Allocation.id == allocation_id).all()
            if len(allocations) == 0:
                return self.error("Could not retrieve allocation.")
            return self.success(data=allocations[0])

        instrument_id = self.get_query_argument('instrument_id', None)
        if instrument_id is not None:
            allocations = allocations.filter(Allocation.instrument_id == instrument_id)

        allocations = allocations.all()
        self.verify_permissions()
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
        try:
            allocation = Allocation.__schema__().load(data=data)
        except ValidationError as e:
            return self.error(
                f'Error parsing posted allocation: "{e.normalized_messages()}"'
            )

        group = Group.get_if_accessible_by(allocation.group_id, self.current_user)
        if group is None:
            return self.error(f'No group with specified ID: {allocation.group_id}')

        instrument = Instrument.get_if_accessible_by(
            allocation.instrument_id, self.current_user
        )
        if instrument is None:
            return self.error(f'No group with specified ID: {allocation.instrument_id}')

        DBSession().add(allocation)
        self.finalize_transaction()
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
        allocation = Allocation.get_if_accessible_by(
            int(allocation_id), self.current_user, mode="update"
        )

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
        self.finalize_transaction()
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
        allocation = Allocation.get_if_accessible_by(
            int(allocation_id), self.current_user, mode='delete'
        )
        DBSession().delete(allocation)
        self.finalize_transaction()
        return self.success()
