import arrow
import astropy.units as u
from astropy.time import Time, TimeDelta
import asyncio
import jsonschema
from marshmallow.exceptions import ValidationError
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token, permissions

from ...models import (
    Allocation,
    EventObservationPlan,
    Group,
    Obj,
    Localization,
    MovingObject,
    MovingObjectAssociation,
    ObservationPlanRequest,
)
from ..base import BaseHandler
from ...utils.moving_objects import get_object_positions
from .gcn import add_tiles_properties_contour_and_obsplan

MAX_MOVING_OBJECTS = 1000


class MovingObjectHandler(BaseHandler):
    @auth_or_token
    def get(self, moving_object_id=None):
        """
        ---
        single:
          tags:
            - moving_objects
          description: Retrieve a moving object
          parameters:
            - in: path
              name: moving_object_id
              required: true
              schema:
                type: integer
          responses:
            200:
               content:
                application/json:
                  schema: SingleMovingObject
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          tags:
            - moving_objects
          description: Retrieve all moving objects
          parameters:
          - in: query
            name: moving_objectID
            nullable: true
            schema:
                type: string
            description: Retrieve moving object that matches the moving_objectID.
          - in: query
            name: obj_id
            nullable: true
            schema:
              type: number
            description: Retrieve moving objects associated with list of obj_id.
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of moving objects to return per paginated request. Defaults to 10. Can be no larger than {MAX_MOVING_OBJECTS}.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for paginated query results. Defaults to 1.
          - in: query
            name: include_objs
            nullable: true
            schema:
                type: boolean
            description: |
                Include the associated objects in the response. Defaults to False.
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfMovingObjects
            400:
              content:
                application/json:
                  schema: Error
        """

        # get owned moving objects

        with self.Session() as session:
            moving_objects = MovingObject.select(session.user_or_token)

            if moving_object_id is not None:
                try:
                    moving_object_id = str(moving_object_id)
                except ValueError:
                    return self.error("MovingObject ID must be a valid integer.")

                moving_object = MovingObject.select(session.user_or_token).where(
                    MovingObject.id == moving_object_id
                )
                moving_object = session.scalars(moving_object).first()
                if moving_object is None:
                    return self.error("Could not retrieve moving object.")

                table = moving_object.table.to_pandas().to_dict('records')
                moving_object = {
                    **moving_object.to_dict(),
                    'table': table,
                    'objs': [o.to_dict() for o in moving_object.objs if o is not None],
                }

                return self.success(data=moving_object)

            page_number = self.get_query_argument("pageNumber", 1)
            n_per_page = self.get_query_argument("numPerPage", 10)
            obj_id = self.get_query_argument("obj_id", None)
            moving_objectID = self.get_query_argument("moving_objectID", None)
            include_objs = self.get_query_argument("include_objs", False)
            include_plans = self.get_query_argument("include_plans", True)

            if include_plans:
                options = [
                    joinedload(MovingObject.observationplan_requests)
                    .joinedload(ObservationPlanRequest.observation_plans)
                    .joinedload(EventObservationPlan.statistics)
                ]
            else:
                options = []

            moving_objects = MovingObject.select(session.user_or_token, options=options)

            if obj_id is not None:
                moving_objects = moving_objects.join(
                    MovingObjectAssociation,
                    MovingObjectAssociation.moving_object_id == MovingObject.id,
                ).where(MovingObjectAssociation.obj_id == obj_id)

            if moving_objectID is not None:
                moving_objects = moving_objects.where(
                    MovingObject.id.like(f'%{moving_objectID}%')
                )

            try:
                page_number = int(page_number)
            except ValueError:
                return self.error("Invalid page number value.")

            try:
                n_per_page = int(n_per_page)
            except (ValueError, TypeError) as e:
                return self.error(f"Invalid numPerPage value: {str(e)}")

            if n_per_page > MAX_MOVING_OBJECTS:
                return self.error(
                    f'numPerPage should be no larger than {MAX_MOVING_OBJECTS}.'
                )

            count_stmt = sa.select(sa.func.count()).select_from(moving_objects)
            total_matches = session.execute(count_stmt).scalar()

            if n_per_page is not None:
                moving_objects = (
                    moving_objects.distinct()
                    .limit(n_per_page)
                    .offset((page_number - 1) * n_per_page)
                )

            moving_objects = session.scalars(moving_objects).unique().all()
            moving_objects_data = []
            for moving_object in moving_objects:
                if include_objs:
                    objs = [o.to_dict() for o in moving_object.objs if o is not None]
                if include_plans:
                    plans = [
                        o.to_dict()
                        for o in moving_object.observationplan_requests
                        if o is not None
                    ]
                moving_object = {
                    **moving_object.to_dict(),
                    'contour': moving_object.contour,
                }
                if include_objs:
                    moving_object['objs'] = objs
                if include_plans:
                    moving_object['plans'] = plans
                moving_objects_data.append(moving_object)

            return self.success(
                data={
                    'moving_objects': moving_objects_data,
                    "totalMatches": int(total_matches),
                    "pageNumber": page_number,
                    "numPerPage": n_per_page,
                }
            )

    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Post new moving object
        tags:
          - moving_objects
        requestBody:
          content:
            application/json:
              schema: MovingObjectNoID
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
                              description: New moving object ID
        """

        data = self.get_json()
        obj_ids = data.pop('obj_ids', [])
        with self.Session() as session:
            if 'id' not in data:
                return self.error("Moving object ID (name) must be provided.")

            # look if the moving object already exists
            moving_object = session.scalar(
                MovingObject.select(session.user_or_token).where(
                    MovingObject.id == str(data['id'])
                )
            )
            if moving_object is not None:
                return self.error(f"Moving object with ID {data['id']} already exists.")
            try:
                moving_object = MovingObject.__schema__().load(data=data)
            except ValidationError as e:
                return self.error(
                    f'Error parsing posted moving_object: "{e.normalized_messages()}"'
                )

            session.add(moving_object)

            if len(obj_ids) > 0:
                for obj_id in obj_ids:
                    obj = session.scalar(
                        Obj.select(session.user_or_token).where(Obj.id == obj_id)
                    )
                    if obj is None:
                        return self.error(f"Could not find object with ID {obj_id}")
                    moving_object_association = MovingObjectAssociation(
                        obj=obj, moving_object=moving_object
                    )
                    session.add(moving_object_association)
            session.commit()

            self.push_all(action="skyportal/REFRESH_MOVING_OBJECTS")
            return self.success(data={"id": moving_object.id})

    @permissions(['Upload data'])
    def put(self, moving_object_id):
        """
        ---
        description: Update a moving object
        tags:
          - moving_objects
        parameters:
          - in: path
            name: moving_object_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: MovingObjectNoID
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
            moving_object = session.scalars(
                MovingObject.select(session.user_or_token, mode="update").where(
                    MovingObject.id == str(moving_object_id)
                )
            ).first()
            if moving_object is None:
                return self.error('No such moving_object')

            data = self.get_json()
            data['id'] = moving_object_id

            obj_ids = data.pop('obj_ids', [])

            schema = MovingObject.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )

            for k in data:
                setattr(moving_object, k, data[k])

            if len(obj_ids) > 0:
                # delete the existing associations
                existing_obj_ids = [o.id for o in moving_object.objs]
                obj_ids_to_delete = set(existing_obj_ids) - set(obj_ids)
                obj_ids_to_add = set(obj_ids) - set(existing_obj_ids)
                for obj_id in obj_ids_to_delete:
                    moving_object_association = (
                        MovingObjectAssociation.select()
                        .where(
                            (MovingObjectAssociation.obj_id == obj_id)
                            & (
                                MovingObjectAssociation.moving_object_id
                                == moving_object_id
                            )
                        )
                        .first()
                    )
                    if moving_object_association is not None:
                        session.delete(moving_object_association)
                for obj_id in obj_ids_to_add:
                    obj = session.scalar(
                        Obj.select(session.user_or_token).where(Obj.id == obj_id)
                    )
                    if obj is None:
                        return self.error(f"Could not find object with ID {obj_id}")
                    moving_object_association = MovingObjectAssociation(
                        obj=obj, moving_object=moving_object
                    )
                    session.add(moving_object_association)

            session.commit()

            self.push_all(action="skyportal/REFRESH_MOVING_OBJECTS")
            return self.success({"id": moving_object_id})

    @permissions(['Upload data'])
    def delete(self, moving_object_id):
        """
        ---
        description: Delete a moving object.
        tags:
          - moving_objects
        parameters:
          - in: path
            name: moving_object_id
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
            moving_object = session.scalars(
                MovingObject.select(session.user_or_token, mode="delete").where(
                    MovingObject.id == str(moving_object_id)
                )
            ).first()
            if moving_object is None:
                return self.error('No such moving_object')

            session.delete(moving_object)
            session.commit()

            self.push_all(action="skyportal/REFRESH_MOVING_OBJECTS")
            return self.success()


class MovingObjectHorizonsHandler(BaseHandler):
    @permissions(['Upload data'])
    async def post(self):
        """
        ---
        description: Upload data from JPL Horizons.
        tags:
          - moving_objects
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                    object_name:
                        type: string
                        description: Name of the moving object.
                    start_date:
                        type: string
                        description: Start date for the query
                    end_date:
                        type: string
                        description: End date for the query
                    time_step:
                        type: string
                        description: Time step for the query
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

        object_name = data.get('object_name')
        if object_name is None:
            return self.error('object_name is required')

        try:
            if 'start_date' in data:
                start_date = arrow.get(data['start_date'].strip()).datetime
            else:
                start_date = Time.now() - TimeDelta(3 * u.day)
        except Exception as e:
            return self.error(f'Error parsing start_date: {e}')
        try:
            if 'end_date' in data:
                end_date = arrow.get(data['end_date'].strip()).datetime
            else:
                end_date = Time.now() + TimeDelta(1 * u.day)
        except Exception as e:
            return self.error(f'Error parsing end_date: {e}')

        time_step = data.get("time_step", "60m")

        pos = get_object_positions(
            object_name,
            start_date.datetime,
            end_date.datetime,
            time_step=time_step,
            verbose=True,
        )
        if pos is None or 'ra' not in pos or len(pos['ra']) == 0:
            return self.error('No positions found for object')

        pos["id"] = object_name

        with self.Session() as session:
            # if the moving object already exists, update it
            moving_object = session.scalar(
                MovingObject.select(session.user_or_token).where(
                    MovingObject.id == object_name
                )
            )
            if moving_object is not None:
                schema = MovingObject.__schema__()
                try:
                    schema.load(data=pos, partial=True)
                except ValidationError as e:
                    return self.error(
                        'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                    )

                for k in pos:
                    setattr(moving_object, k, pos[k])
                session.commit()
                self.push_all(action="skyportal/REFRESH_MOVING_OBJECTS")
                return self.success(data={"id": moving_object.id})
            else:
                try:
                    moving_object = MovingObject.__schema__().load(data=pos)
                except ValidationError as e:
                    return self.error(
                        f'Error parsing posted moving_object: "{e.normalized_messages()}"'
                    )

                session.add(moving_object)
                session.commit()
                self.push_all(action="skyportal/REFRESH_MOVING_OBJECTS")
                return self.success(data={"id": moving_object.id})


class MovingObjectObservationPlanRequestHandler(BaseHandler):
    @permissions(['Manage observation plans'])
    def post(self):
        """
        ---
        description: Create moving object observation plan requests.
        tags:
          - moving_objects
        requestBody:
          content:
            application/json:
              schema: MovingObjectObservationPlanPost
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
                              description: New moving object observation plan request ID
        """
        data = self.get_json()
        asynchronous = data.pop('asynchronous', True)

        with self.Session() as session:
            moving_object_id = data.pop('name')
            if moving_object_id is None:
                return self.error('moving_object name is required')

            moving_object = session.scalars(
                MovingObject.select(session.user_or_token).where(
                    MovingObject.id == str(moving_object_id)
                )
            ).first()
            if moving_object is None:
                return self.error('No such moving_object')

            if 'queue_name' not in data.get('payload', {}):
                return self.error(
                    'All observation plans must have a "queue_name" key in their payload.'
                )

            target_group_ids = data.pop('target_group_ids', [])
            stmt = Group.select(self.current_user).where(Group.id.in_(target_group_ids))
            target_groups = session.scalars(stmt).all()

            stmt = Allocation.select(session.user_or_token).where(
                Allocation.id == data['allocation_id'],
            )
            allocation = session.scalars(stmt).first()
            if allocation is None:
                return self.error(
                    f"Cannot access allocation with ID: {data['allocation_id']}",
                    status=403,
                )

            instrument = allocation.instrument
            if instrument.api_classname_obsplan is None:
                return self.error('Instrument has no remote API.', status=403)

            try:
                formSchema = instrument.api_class_obsplan.custom_json_schema(
                    instrument, self.current_user
                )
            except AttributeError:
                formSchema = instrument.api_class_obsplan.form_json_schema

            payload = data['payload']

            # validate the payload
            try:
                jsonschema.validate(payload, formSchema)
            except jsonschema.exceptions.ValidationError as e:
                return self.error(f'Payload failed to validate: {e}', status=403)

            filters = payload.get('filters', [])
            if isinstance(filters, str):
                filters = filters.split(',')
            if (
                not set(filters).issubset(set(allocation.instrument.filters))
                or len(filters) == 0
            ):
                return self.error(
                    f'Filters in payload must be a subset of instrument filters: {allocation.instrument.filters}'
                )

            url, properties, tags = None, None, None
            try:
                skymap = moving_object.skymap
            except Exception as e:
                raise ValueError(
                    f"Failed to get skymap from moving object {moving_object.id}: {e}"
                )

            if skymap is None:
                raise Exception(
                    f"No skymap could be created for moving object {moving_object.id}"
                )

            localization = Localization(
                **skymap, sent_by_id=self.associated_user_object.id
            )
            session.add(localization)
            session.commit()
            localization_id = localization.id

            if asynchronous:
                try:
                    loop = asyncio.get_event_loop()
                except Exception:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                IOLoop.current().run_in_executor(
                    None,
                    lambda: add_tiles_properties_contour_and_obsplan(
                        localization_id,
                        self.associated_user_object.id,
                        url=url,
                        notify=False,
                        properties=properties,
                        tags=tags,
                        observation_plans=False,
                    ),
                )
            else:
                add_tiles_properties_contour_and_obsplan(
                    localization_id,
                    self.associated_user_object.id,
                    session,
                    url=url,
                    notify=False,
                    properties=properties,
                    tags=tags,
                    observation_plans=False,
                )

            plan = {}
            plan["requester_id"] = self.associated_user_object.id
            plan["last_modified_by_id"] = self.associated_user_object.id
            plan['allocation_id'] = int(allocation.id)
            plan['localization_id'] = int(localization.id)
            plan['moving_object_id'] = moving_object.id
            plan['default_plan'] = False
            plan['payload'] = payload

            observation_plan_request = ObservationPlanRequest.__schema__().load(plan)
            observation_plan_request.target_groups = target_groups
            session.add(observation_plan_request)
            session.commit()
