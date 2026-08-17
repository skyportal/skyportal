import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions

from ...models import Obj, SuperObj
from ...utils.parse import str_to_bool
from ..base import BaseHandler


def super_obj_to_dict(super_obj):
    """Serialize a SuperObj with its linked Obj positions."""
    return {
        "id": super_obj.id,
        "name": super_obj.name,
        "is_roid": super_obj.is_roid,
        "created_at": super_obj.created_at,
        "objs": [
            {"id": obj.id, "ra": obj.ra, "dec": obj.dec} for obj in super_obj.objs
        ],
    }


async def load_objs(session, obj_ids):
    """Load the given Objs, erroring if any are missing or inaccessible."""
    obj_ids = list(dict.fromkeys(obj_ids))
    objs = (
        (
            await session.scalars(
                Obj.select(session.user_or_token).where(Obj.id.in_(obj_ids))
            )
        )
        .unique()
        .all()
    )
    missing = set(obj_ids) - {obj.id for obj in objs}
    if missing:
        raise ValueError(f"Could not load Objs: {', '.join(sorted(missing))}")
    return objs


class SuperObjHandler(BaseHandler):
    @auth_or_token
    async def post(self):
        """
        ---
        summary: Create a SuperObj
        description: |
          Create a SuperObj linking multiple Objs that represent the same
          astrophysical object, e.g. detections of one asteroid on separate
          nights, or the same transient reported by different surveys.
        tags:
          - super objs
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                    description: Name of the super-object, e.g. an MPC designation.
                  is_roid:
                    type: boolean
                    description: Whether the super-object is a moving object.
                  obj_ids:
                    type: array
                    items:
                      type: string
                    description: IDs of the Objs to link.
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
                              description: New SuperObj ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()

        name = data.get("name")
        if name is not None and not str(name).strip():
            return self.error("name must be a non-empty string")

        obj_ids = data.get("obj_ids", [])
        if not isinstance(obj_ids, list):
            return self.error("obj_ids must be a list")

        try:
            is_roid = str_to_bool(data.get("is_roid", False))
        except ValueError:
            return self.error("Invalid is_roid value")

        async with self.AsyncSession() as session:
            super_obj = SuperObj(name=name, is_roid=is_roid)
            if obj_ids:
                try:
                    super_obj.objs = await load_objs(session, obj_ids)
                except ValueError as e:
                    return self.error(str(e))

            session.add(super_obj)
            await session.commit()

            self.push_all(action="skyportal/REFRESH_SUPER_OBJS")
            return self.success(data={"id": super_obj.id})

    @auth_or_token
    async def get(self, super_obj_id=None):
        """
        ---
        single:
          summary: Retrieve a SuperObj
          tags:
            - super objs
          parameters:
            - in: path
              name: super_obj_id
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
        multiple:
          summary: Retrieve multiple SuperObjs
          tags:
            - super objs
          parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by (partial) name
            - in: query
              name: isRoid
              schema:
                type: boolean
              description: Filter by moving-object status
            - in: query
              name: objID
              schema:
                type: string
              description: Only SuperObjs linking this Obj
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
        async with self.AsyncSession() as session:
            options = [selectinload(SuperObj.objs)]

            if super_obj_id is not None:
                try:
                    super_obj_id = int(super_obj_id)
                except (TypeError, ValueError):
                    return self.error(f"Invalid super_obj_id: {super_obj_id}")

                super_obj = await session.scalar(
                    SuperObj.select(session.user_or_token, options=options).where(
                        SuperObj.id == super_obj_id
                    )
                )
                if super_obj is None:
                    return self.error(f"Could not load SuperObj {super_obj_id}")
                return self.success(data=super_obj_to_dict(super_obj))

            stmt = SuperObj.select(session.user_or_token, options=options)

            name = self.get_query_argument("name", None)
            if name is not None:
                stmt = stmt.where(SuperObj.name.contains(name))

            is_roid = self.get_query_argument("isRoid", None)
            if is_roid is not None:
                try:
                    stmt = stmt.where(SuperObj.is_roid.is_(str_to_bool(is_roid)))
                except ValueError:
                    return self.error("Invalid isRoid value")

            obj_id = self.get_query_argument("objID", None)
            if obj_id is not None:
                stmt = stmt.where(SuperObj.objs.any(Obj.id == obj_id))

            result = await session.scalars(stmt)
            return self.success(
                data=[super_obj_to_dict(s) for s in result.unique().all()]
            )

    @auth_or_token
    async def patch(self, super_obj_id):
        """
        ---
        summary: Update a SuperObj
        description: |
          Update a SuperObj's metadata or membership. `obj_ids` replaces the
          membership wholesale; `add_obj_ids` and `remove_obj_ids` modify it
          incrementally and may not be combined with `obj_ids`.
        tags:
          - super objs
        parameters:
          - in: path
            name: super_obj_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  is_roid:
                    type: boolean
                  obj_ids:
                    type: array
                    items:
                      type: string
                  add_obj_ids:
                    type: array
                    items:
                      type: string
                  remove_obj_ids:
                    type: array
                    items:
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
        try:
            super_obj_id = int(super_obj_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid super_obj_id: {super_obj_id}")

        data = self.get_json()

        replace_ids = data.get("obj_ids")
        add_ids = data.get("add_obj_ids")
        remove_ids = data.get("remove_obj_ids")

        if replace_ids is not None and (add_ids is not None or remove_ids is not None):
            return self.error(
                "obj_ids cannot be combined with add_obj_ids or remove_obj_ids"
            )
        for key, value in (
            ("obj_ids", replace_ids),
            ("add_obj_ids", add_ids),
            ("remove_obj_ids", remove_ids),
        ):
            if value is not None and not isinstance(value, list):
                return self.error(f"{key} must be a list")

        async with self.AsyncSession() as session:
            super_obj = await session.scalar(
                SuperObj.select(
                    session.user_or_token,
                    mode="update",
                    options=[selectinload(SuperObj.objs)],
                ).where(SuperObj.id == super_obj_id)
            )
            if super_obj is None:
                return self.error(f"Could not load SuperObj {super_obj_id}")

            if "name" in data:
                name = data["name"]
                if name is not None and not str(name).strip():
                    return self.error("name must be a non-empty string")
                super_obj.name = name

            if "is_roid" in data:
                try:
                    super_obj.is_roid = str_to_bool(data["is_roid"])
                except ValueError:
                    return self.error("Invalid is_roid value")

            try:
                if replace_ids is not None:
                    super_obj.objs = await load_objs(session, replace_ids)
                else:
                    if add_ids:
                        existing = {obj.id for obj in super_obj.objs}
                        for obj in await load_objs(session, add_ids):
                            if obj.id not in existing:
                                super_obj.objs.append(obj)
                    if remove_ids:
                        removing = set(remove_ids)
                        super_obj.objs = [
                            obj for obj in super_obj.objs if obj.id not in removing
                        ]
            except ValueError as e:
                return self.error(str(e))

            await session.commit()

            self.push_all(action="skyportal/REFRESH_SUPER_OBJS")
            return self.success()

    @permissions(["System admin"])
    async def delete(self, super_obj_id):
        """
        ---
        summary: Delete a SuperObj
        description: |
          Delete a SuperObj. The Objs it links are left untouched; only the
          association is removed.
        tags:
          - super objs
        parameters:
          - in: path
            name: super_obj_id
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
        try:
            super_obj_id = int(super_obj_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid super_obj_id: {super_obj_id}")

        async with self.AsyncSession() as session:
            super_obj = await session.scalar(
                SuperObj.select(session.user_or_token, mode="delete").where(
                    SuperObj.id == super_obj_id
                )
            )
            if super_obj is None:
                return self.error(f"Could not load SuperObj {super_obj_id}")

            await session.execute(
                sa.delete(SuperObj).where(SuperObj.id == super_obj_id)
            )
            await session.commit()

            self.push_all(action="skyportal/REFRESH_SUPER_OBJS")
            return self.success()
