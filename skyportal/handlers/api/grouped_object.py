from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import GroupedObject, Obj


class GroupedObjectHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        summary: Create a new grouped object
        tags:
          - grouped_objects
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                    description: Name/identifier for the grouped object
                    required: true
                  type:
                    type: string
                    description: Type of grouped object (e.g., 'moving_object', 'duplicate_detection')
                    required: true
                  description:
                    type: string
                    description: Optional description of why these objects are related
                    required: false
                  obj_ids:
                    type: array
                    items:
                      type: string
                    description: List of Obj IDs to include in this group
                    required: true
                  properties:
                    type: object
                    description: Additional metadata about this grouped object
                    required: false
                  origin:
                    type: string
                    description: Source/origin of the grouped object (e.g. pipeline name, script identifier)
                    required: false
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

        with self.Session() as session:
            name = data.get('name')
            type = data.get('type')
            obj_ids = data.get('obj_ids', [])

            if not name:
                return self.error('name is required')
            if not type:
                return self.error('type is required')
            if not obj_ids:
                return self.error('obj_ids is required')

            # Verify objects exist and are accessible
            objs = session.scalars(
                Obj.select(self.current_user).where(Obj.id.in_(obj_ids))
            ).all()
            found_ids = {obj.id for obj in objs}
            missing_ids = set(obj_ids) - found_ids
            if missing_ids:
                return self.error(f'Invalid/inaccessible object IDs: {missing_ids}')

            try:
                # Create grouped object
                grouped_obj = GroupedObject(
                    name=name,
                    type=type,
                    description=data.get('description'),
                    properties=data.get('properties'),
                    created_by_id=self.associated_user_object.id,
                    origin=data.get('origin'),
                )

                print(grouped_obj)

                session.add(grouped_obj)
                session.commit()

                return self.success(data={'id': grouped_obj.id})

            except Exception as e:
                return self.error(f'Error creating grouped object: {str(e)}')

    @auth_or_token
    def get(self, grouped_object_id=None):
        """
        ---
        single:
          summary: Retrieve a grouped object
          parameters:
            - in: path
              name: grouped_object_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleGroupedObject
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Retrieve all grouped objects
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfGroupedObjects
        """
        with self.Session() as session:
            if grouped_object_id is not None:
                stmt = GroupedObject.select(self.current_user).where(
                    GroupedObject.id == int(grouped_object_id)
                )
                grouped_obj = session.scalars(stmt).first()
                if grouped_obj is None:
                    return self.error('Invalid grouped object ID')

                result = grouped_obj.to_dict()
                result['created_by'] = grouped_obj.created_by.to_dict()
                return self.success(data=result)

            stmt = GroupedObject.select(self.current_user)
            grouped_objs = session.scalars(stmt).all()

            results = []
            for obj in grouped_objs:
                result = obj.to_dict()
                result['created_by'] = obj.created_by.to_dict()
                results.append(result)

            return self.success(data=results)

    @permissions(['Upload data'])
    def delete(self, grouped_object_id):
        """
        ---
        summary: Delete a grouped object
        parameters:
          - in: path
            name: grouped_object_id
            required: true
            schema:
              type: string
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
            stmt = GroupedObject.select(self.current_user, mode='delete').where(
                GroupedObject.id == grouped_object_id
            )
            grouped_obj = session.scalars(stmt).first()
            if grouped_obj is None:
                return self.error('Invalid grouped object ID')

            session.delete(grouped_obj)
            self.verify_and_commit()

            return self.success()
