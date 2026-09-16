from typing import ClassVar

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions

from ...models import Obj, SuperObj
from ...utils.parse import get_page_and_n_per_page
from ..base import BaseHandler


class SuperObjGetQuery(BaseModel):
    """Query parameters for retrieving SuperObjs."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    name: str | None = Field(
        default=None,
        description="Filter by (partial) name",
    )
    isRoid: bool | None = Field(
        default=None,
        description="Filter by moving-object status",
    )
    objID: str | None = Field(
        default=None,
        description="Only SuperObjs linking this Obj",
    )
    includeEpochs: bool = Field(
        default=False,
        description="Include each linked Obj's thumbnails and annotations. A "
        "scanning view needs them; a plain listing does not, and they cost a "
        "query each.",
    )
    pageNumber: int = Field(default=1, description="Page number, starting at 1.")
    numPerPage: int = Field(
        default=100, description="SuperObjs per page, capped at 500."
    )


class SuperObjPostBody(BaseModel):
    """Request body for creating a SuperObj."""

    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    name: str | None = Field(
        default=None, description="Name of the super-object, e.g. an MPC designation."
    )
    is_roid: bool = Field(
        default=False, description="Whether the super-object is a moving object."
    )
    obj_ids: list[str] = Field(
        default_factory=list, description="IDs of the Objs to link."
    )


class SuperObjPatchBody(BaseModel):
    """Request body for updating a SuperObj."""

    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    name: str | None = Field(default=None, description="Name of the super-object.")
    is_roid: bool | None = Field(
        default=None, description="Whether the super-object is a moving object."
    )
    obj_ids: list[str] | None = Field(
        default=None, description="IDs of the Objs to link, replacing the current ones."
    )
    add_obj_ids: list[str] | None = Field(
        default=None, description="IDs of Objs to add to the current ones."
    )
    remove_obj_ids: list[str] | None = Field(
        default=None, description="IDs of Objs to remove from the current ones."
    )


def super_obj_to_dict(super_obj, epochs=False):
    """Serialize a SuperObj with its linked Obj positions.

    With ``epochs``, each Obj also carries its thumbnails and annotations, which
    is what a reviewer needs to judge a moving object: one column of cutouts per
    detection. Epochs are ordered by time so the columns read left to right.
    """
    objs = list(super_obj.objs)
    if epochs:
        objs.sort(key=lambda o: (o.created_at is None, o.created_at, o.id))
    out = {
        "id": super_obj.id,
        "name": super_obj.name,
        "is_roid": super_obj.is_roid,
        "created_at": super_obj.created_at,
        "objs": [{"id": obj.id, "ra": obj.ra, "dec": obj.dec} for obj in objs],
    }
    if epochs:
        for entry, obj in zip(out["objs"], objs, strict=True):
            entry["created_at"] = obj.created_at
            entry["thumbnails"] = [
                {
                    "id": t.id,
                    "type": t.type,
                    "public_url": t.public_url,
                    "origin": t.origin,
                }
                for t in (obj.thumbnails or [])
            ]
            entry["annotations"] = [
                {"origin": a.origin, "data": a.data} for a in (obj.annotations or [])
            ]
    return out


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
    async def post(self, *, body: SuperObjPostBody = None):
        """
        ---
        summary: Create a SuperObj
        description: |
          Create a SuperObj linking multiple Objs that represent the same
          astrophysical object, e.g. detections of one asteroid on separate
          nights, or the same transient reported by different surveys.
        tags:
          - super objs
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
        body = self.parse_body(SuperObjPostBody)

        if body.name is not None and not body.name.strip():
            return self.error("name must be a non-empty string")

        async with self.AsyncSession() as session:
            super_obj = SuperObj(name=body.name, is_roid=body.is_roid)
            if body.obj_ids:
                try:
                    super_obj.objs = await load_objs(session, body.obj_ids)
                except ValueError as e:
                    return self.error(str(e))

            session.add(super_obj)
            await session.commit()

            self.push_all(action="skyportal/REFRESH_SUPER_OBJS")
            return self.success(data={"id": super_obj.id})

    @auth_or_token
    async def get(
        self,
        super_obj_id: int | None = None,
        *,
        query: SuperObjGetQuery = None,
    ):
        """
        ---
        single:
          summary: Retrieve a SuperObj
          tags:
            - super objs
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
        query = self.parse_query(SuperObjGetQuery)

        try:
            page_number, n_per_page = get_page_and_n_per_page(
                query.pageNumber, query.numPerPage
            )
        except ValueError as e:
            return self.error(str(e))

        async with self.AsyncSession() as session:
            options = [selectinload(SuperObj.objs)]
            if query.includeEpochs:
                options = [
                    selectinload(SuperObj.objs).selectinload(Obj.thumbnails),
                    selectinload(SuperObj.objs).selectinload(Obj.annotations),
                ]

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
                return self.success(
                    data=super_obj_to_dict(super_obj, epochs=query.includeEpochs)
                )

            stmt = SuperObj.select(session.user_or_token, options=options)

            if query.name is not None:
                stmt = stmt.where(SuperObj.name.contains(query.name))

            if query.isRoid is not None:
                stmt = stmt.where(SuperObj.is_roid.is_(query.isRoid))

            if query.objID is not None:
                stmt = stmt.where(SuperObj.objs.any(Obj.id == query.objID))

            total = await session.scalar(
                sa.select(sa.func.count()).select_from(stmt.subquery())
            )
            result = await session.scalars(
                stmt.order_by(SuperObj.created_at.desc(), SuperObj.id.desc())
                .limit(n_per_page)
                .offset((page_number - 1) * n_per_page)
            )
            return self.success(
                data={
                    "superObjs": [
                        super_obj_to_dict(s, epochs=query.includeEpochs)
                        for s in result.unique().all()
                    ],
                    "totalMatches": total,
                    "pageNumber": page_number,
                    "numPerPage": n_per_page,
                }
            )

    @auth_or_token
    async def patch(self, super_obj_id: int, *, body: SuperObjPatchBody = None):
        """
        ---
        summary: Update a SuperObj
        description: |
          Update a SuperObj's metadata or membership. `obj_ids` replaces the
          membership wholesale; `add_obj_ids` and `remove_obj_ids` modify it
          incrementally and may not be combined with `obj_ids`.
        tags:
          - super objs
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

        body = self.parse_body(SuperObjPatchBody)
        data = body.model_dump(exclude_unset=True)

        replace_ids = body.obj_ids
        add_ids = body.add_obj_ids
        remove_ids = body.remove_obj_ids

        if replace_ids is not None and (add_ids is not None or remove_ids is not None):
            return self.error(
                "obj_ids cannot be combined with add_obj_ids or remove_obj_ids"
            )

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
                if body.name is not None and not body.name.strip():
                    return self.error("name must be a non-empty string")
                super_obj.name = body.name

            if "is_roid" in data:
                super_obj.is_roid = body.is_roid

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
    async def delete(self, super_obj_id: int):
        """
        ---
        summary: Delete a SuperObj
        description: |
          Delete a SuperObj. The Objs it links are left untouched; only the
          association is removed.
        tags:
          - super objs
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
