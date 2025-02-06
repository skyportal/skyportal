from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import GroupedObject, Obj
import sqlalchemy as sa


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

                session.add(grouped_obj)
                session.commit()

                result = grouped_obj.to_dict()
                result['created_by'] = grouped_obj.created_by.to_dict()
                return self.success(data=result)

            except Exception as e:
                return self.error(f'Error creating grouped object: {str(e)}')

    @auth_or_token
    def get(self, grouped_object_name=None):
        """
        ---
        single:
          summary: Retrieve a grouped object
          parameters:
            - in: path
              name: grouped_object_name
              required: true
              schema:
                type: string
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
            if grouped_object_name is not None:
                stmt = (
                    GroupedObject.select(self.current_user)
                    .where(GroupedObject.name == grouped_object_name)
                    .options(sa.orm.joinedload(GroupedObject.objs))
                )
                grouped_obj = session.scalars(stmt).first()
                if grouped_obj is None:
                    return self.error('Invalid grouped object name', status=404)

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
    def delete(self, grouped_object_name):
        """
        ---
        summary: Delete a grouped object
        parameters:
          - in: path
            name: grouped_object_name
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
                GroupedObject.name == grouped_object_name
            )
            grouped_obj = session.scalars(stmt).first()
            if grouped_obj is None:
                return self.error('Invalid grouped object name', status=404)

            session.delete(grouped_obj)
            session.commit()

            result = grouped_obj.to_dict()
            result['created_by'] = grouped_obj.created_by.to_dict()
            return self.success(data=result)

    @permissions(['Upload data'])
    def patch(self, grouped_object_name):
        """
        ---
        summary: Update a grouped object
        tags:
          - grouped_objects
        parameters:
          - in: path
            name: grouped_object_name
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  type:
                    type: string
                    description: Type of grouped object
                  description:
                    type: string
                    description: Optional description
                  obj_ids:
                    type: array
                    items:
                      type: string
                    description: List of Obj IDs to include in this group
                  properties:
                    type: object
                    description: Additional metadata about this grouped object
                  origin:
                    type: string
                    description: Source/origin of the grouped object
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
            stmt = GroupedObject.select(self.current_user, mode='update').where(
                GroupedObject.name == grouped_object_name
            )
            grouped_obj = session.scalars(stmt).first()
            if grouped_obj is None:
                return self.error(
                    'Invalid grouped object name or you do not have permission to update this grouped object'
                )

            if 'name' in data:
                return self.error(
                    'Cannot modify the name of a grouped object as it is the primary key'
                )

            if 'obj_ids' in data:
                obj_ids = data['obj_ids']
                # Verify objects exist and are accessible
                objs = session.scalars(
                    Obj.select(self.current_user).where(Obj.id.in_(obj_ids))
                ).all()
                found_ids = {obj.id for obj in objs}
                missing_ids = set(obj_ids) - found_ids
                if missing_ids:
                    return self.error(f'Invalid/inaccessible object IDs: {missing_ids}')
                grouped_obj.objs = objs

            # Update other fields if provided
            if 'type' in data:
                grouped_obj.type = data['type']
            if 'description' in data:
                grouped_obj.description = data['description']
            if 'properties' in data:
                grouped_obj.properties = data['properties']
            if 'origin' in data:
                grouped_obj.origin = data['origin']

            try:
                session.commit()
                result = grouped_obj.to_dict()
                result['created_by'] = grouped_obj.created_by.to_dict()
                return self.success(data=result)
            except Exception as e:
                return self.error(f'Error updating grouped object: {str(e)}')
