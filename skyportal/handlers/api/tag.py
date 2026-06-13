"""API handlers for managing tags and tag options.

This module provides REST API endpoints for:
- Managing tag options (create, read, update, delete tag options)
- Managing object-tag associations (create, read, delete associations between objects and tags)
"""

import re

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env

from ...models import Group, GroupObjTag, Obj, ObjTag, ObjTagOption, SuperObj
from ...utils.parse import str_to_bool
from ..base import BaseHandler

env, cfg = load_env()


class ObjTagOptionHandler(BaseHandler):
    """Handler for managing tag options.

    Tag options define the available tags that can be applied to objects.
    They include a name and optional color for display purposes.
    """

    @auth_or_token
    async def get(self):
        """
        ---
        summary: Retrieve all tag options
        description: Retrieve all available tag options accessible to the user
        tags:
          - object tags
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
                          type: array
                          items:
                            $ref: '#/components/schemas/ObjTagOption'
        """
        async with self.AsyncSession() as session:
            tags = (await session.scalars(ObjTagOption.select(session.user_or_token))).all()
            return self.success(data=tags)

    @permissions(["Manage sources"])
    async def post(self):
        """
        ---
        summary: Create a new tag option
        description: Create a new tag option that can be applied to objects
        tags:
          - object tags
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                    description: Tag name (letters and numbers only)
                  color:
                    type: string
                    description: Hex color code (e.g., #3a87ad)
                required:
                  - name
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
                          $ref: '#/components/schemas/ObjTagOption'
          400:
            content:
              application/json:
                schema: Error
          409:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        name = data.get("name")
        color = data.get("color")

        if not name or not isinstance(name, str):
            return self.error("`name` must be provided as a non-empty string")

        if not re.fullmatch(r"[A-Za-z0-9]+", name):
            return self.error(
                "`name` must contain only letters and numbers (no spaces, underscores, or special characters)",
                status=400,
            )

        if color and not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            return self.error(
                "`color` must be a valid hex color code (e.g., #3a87ad)",
                status=400,
            )

        async with self.AsyncSession() as session:
            existing_tag = await session.scalar(
                ObjTagOption.select(session.user_or_token).where(
                    func.lower(ObjTagOption.name) == name.lower()
                )
            )

            if existing_tag:
                return self.error(
                    f"Tag '{name}' already exists as '{existing_tag.name}' (case-insensitive match)",
                    status=409,
                )

            new_tag = ObjTagOption(name=name, color=color)
            session.add(new_tag)
            await session.commit()

            self.push_all(action="skyportal/FETCH_TAG_OPTIONS")
            return self.success(new_tag)

    @auth_or_token
    async def patch(self, tag_id: int):
        """
        ---
        summary: Update a tag option
        description: Update an existing tag option's name and/or color
        tags:
          - object tags
        parameters:
          - in: path
            name: tag_id
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
                    description: New tag name
                  color:
                    type: string
                    description: New hex color code (e.g., #3a87ad)
                required:
                  - name
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
          404:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        new_name = data.get("name")
        new_color = data.get("color")

        try:
            tag_id = int(tag_id)
        except Exception:
            raise ValueError("Invalid tag ID")

        if not new_name or not isinstance(new_name, str):
            return self.error("`name` must be provided as a non-empty string")

        if not re.fullmatch(r"[A-Za-z0-9]+", new_name):
            return self.error(
                "`name` must contain only letters and numbers (no spaces, underscores, or special characters)",
                status=400,
            )

        if new_color and not re.fullmatch(r"#[0-9A-Fa-f]{6}", new_color):
            return self.error(
                "`color` must be a valid hex color code (e.g., #3a87ad)",
                status=400,
            )

        async with self.AsyncSession() as session:
            tag = await session.scalar(
                ObjTagOption.select(session.user_or_token).where(
                    ObjTagOption.id == tag_id
                )
            )

            if not tag:
                return self.error("Tag not found", status=404)

            if await session.scalar(
                ObjTagOption.select(session.user_or_token)
                .where(ObjTagOption.name == new_name)
                .where(ObjTagOption.id != tag_id)
            ):
                return self.error("This tag name already exists for another tag")

            tag.name = new_name
            if new_color:
                tag.color = new_color
            await session.commit()

            self.push_all(action="skyportal/FETCH_TAG_OPTIONS")
            return self.success()

    @permissions(["Manage sources"])
    async def delete(self, tag_id: int):
        """
        ---
        summary: Delete a tag option
        description: Delete an existing tag option
        tags:
          - object tags
        parameters:
          - in: path
            name: tag_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
          404:
            content:
              application/json:
                schema: Error
        """
        try:
            tag_id = int(tag_id)
        except Exception:
            raise ValueError("Invalid tag ID")

        async with self.AsyncSession() as session:
            tag = await session.scalar(
                ObjTagOption.select(session.user_or_token).where(
                    ObjTagOption.id == tag_id
                )
            )

            if not tag:
                return self.error("Tag not found", status=404)

            await session.delete(tag)
            await session.commit()

            self.push_all(action="skyportal/FETCH_TAG_OPTIONS")
            return self.success(f"Successfully deleted tag {tag}")


class ObjTagHandler(BaseHandler):
    """Handler for managing object-tag associations.

    Manages the relationships between objects and tag options,
    allowing objects to be tagged with specific labels.
    """

    @auth_or_token
    async def get(self):
        """
        ---
        summary: Retrieve object-tag associations
        description: Retrieve all tag-object associations or filter by object ID or tag option ID
        tags:
          - object tags
        parameters:
          - in: query
            name: obj_id
            required: false
            schema:
              type: string
            description: Filter associations by object ID
          - in: query
            name: objtagoption_id
            required: false
            schema:
              type: integer
            description: Filter associations by tag option ID
          - in: query
            name: includeSuperObjs
            required: false
            schema:
              type: boolean
            description: |
              If true and obj_id is given, also return tags on the Objs linked
              to it through a SuperObj (meta-object), as one provenance-tagged
              union (each entry keeps its obj_id). Defaults to false.
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
                          type: array
                          items:
                            $ref: '#/components/schemas/ObjTag'
        """
        obj_id = self.get_query_argument("obj_id", None)
        objtagoption_id = self.get_query_argument("objtagoption_id", None, type=int)
        include_super_objs = str_to_bool(
            self.get_query_argument("includeSuperObjs", "false"), default=False
        )

        async with self.AsyncSession() as session:
            query = ObjTag.select(session.user_or_token)

            if obj_id:
                # Meta-object aggregation: expand to every Obj linked to this one
                # through a SuperObj, returning their tags as one provenance-tagged
                # union (each ObjTag keeps its obj_id). RLS is preserved by the
                # per-row ObjTag.select(user). Mirrors the photometry SuperObjs
                # aggregation; defaults off, so the single-obj path is unchanged.
                obj_ids = {obj_id}
                if include_super_objs:
                    super_objs = (
                        (
                            await session.scalars(
                                sa.select(SuperObj)
                                .options(selectinload(SuperObj.objs))
                                .where(SuperObj.objs.any(Obj.id == obj_id))
                            )
                        )
                        .unique()
                        .all()
                    )
                    for super_obj in super_objs:
                        obj_ids.update({linked_obj.id for linked_obj in super_obj.objs})
                query = query.where(ObjTag.obj_id.in_(obj_ids))
            if objtagoption_id:
                query = query.where(ObjTag.objtagoption_id == objtagoption_id)

            associations = (await session.scalars(query)).all()
            return self.success(associations)

    @auth_or_token
    async def post(self):
        """
        ---
        summary: Create object-tag association
        description: Create a new association between an object and a tag option, with group access
        tags:
          - object tags
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  objtagoption_id:
                    type: integer
                    description: ID of the tag option to associate
                  obj_id:
                    type: string
                    description: ID of the object to tag
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: IDs of groups that can access this tag association
                required:
                  - objtagoption_id
                  - obj_id
                  - group_ids
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
                          $ref: '#/components/schemas/ObjTag'
          400:
            content:
              application/json:
                schema: Error
          404:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        objtagoption_id = data.get("objtagoption_id")
        obj_id = data.get("obj_id")
        group_ids = data.get("group_ids")

        if not objtagoption_id or not obj_id:
            return self.error("Both `objtagoption_id` and `obj_id` must be provided")

        if group_ids is not None:
            if not isinstance(group_ids, list):
                return self.error("`group_ids` must be a list of integers")
            if len(group_ids) > 0:
                try:
                    group_ids = [int(gid) for gid in group_ids]
                except (ValueError, TypeError):
                    return self.error("`group_ids` must be a list of integers")
            else:
                group_ids = None

        async with self.AsyncSession() as session:
            if group_ids is None:
                public_group_id = await session.scalar(
                    sa.select(Group.id).where(
                        Group.name == cfg["misc.public_group_name"]
                    )
                )
                if public_group_id is None:
                    return self.error(
                        f"No group_ids were specified and the public group "
                        f'"{cfg["misc.public_group_name"]}" does not exist. '
                        f"Cannot create tag association."
                    )
                group_ids = [public_group_id]

            # Verify tag option exists
            if not await session.scalar(
                sa.select(ObjTagOption.id).where(ObjTagOption.id == objtagoption_id)
            ):
                return self.error("Specified tag option does not exist", status=404)

            # Verify obj exists
            obj = await session.scalar(sa.select(Obj).where(Obj.id == obj_id))
            if not obj:
                return self.error("Specified obj does not exist", status=404)

            # System admins can add tags to any group
            requested_group_ids = set(group_ids)
            if self.current_user.is_system_admin:
                existing_group_ids = set(
                    (await session.scalars(
                        sa.select(Group.id).where(Group.id.in_(requested_group_ids))
                    )).all()
                )
                if len(existing_group_ids) != len(requested_group_ids):
                    return self.error(
                        "One or more specified groups do not exist", status=404
                    )
                valid_group_ids = requested_group_ids
            else:
                # Regular users can only add tags to their accessible groups
                user_group_ids = {g.id for g in self.current_user.accessible_groups}
                valid_group_ids = requested_group_ids.intersection(user_group_ids)

                if not valid_group_ids:
                    return self.error(
                        "You don't have access to any of the specified groups",
                        status=403,
                    )

            # Check if association already exists
            existing_assoc_id = await session.scalar(
                sa.select(ObjTag.id)
                .where(ObjTag.objtagoption_id == objtagoption_id)
                .where(ObjTag.obj_id == obj_id)
            )

            if existing_assoc_id:
                existing_group_ids = set(
                    (await session.scalars(
                        sa.select(GroupObjTag.group_id).where(
                            GroupObjTag.obj_tag_id == existing_assoc_id
                        )
                    )).all()
                )

                groups_to_add = valid_group_ids - existing_group_ids

                if not groups_to_add:
                    return self.success()

                for group_id in groups_to_add:
                    group_obj_tag = GroupObjTag(
                        group_id=group_id,
                        obj_tag_id=existing_assoc_id,
                    )
                    session.add(group_obj_tag)
                await session.commit()

                self.push_all(
                    action="skyportal/REFRESH_SOURCE",
                    payload={"obj_key": obj.internal_key},
                )
                return self.success(
                    {"id": existing_assoc_id, "message": "Groups added to existing tag"}
                )

            groups = (await session.scalars(
                sa.select(Group).where(Group.id.in_(valid_group_ids))
            )).all()

            new_assoc = ObjTag(
                objtagoption_id=objtagoption_id,
                obj_id=obj_id,
                author_id=self.associated_user_object.id,
            )
            new_assoc.groups = groups
            session.add(new_assoc)
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": obj.internal_key},
            )
            return self.success(new_assoc)

    @auth_or_token
    async def delete(self, association_id: int):
        """
        ---
        summary: Delete object-tag association
        description: >
            Remove group associations with a tag. If group_ids is provided, only those
            specific groups are removed. Otherwise, all user's group associations are removed.
            If no group associations remain after removal, the tag is deleted entirely.
            System admins can remove any group; regular users can only remove their groups.
        tags:
          - object tags
        parameters:
          - in: path
            name: association_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: >
                        Optional list of group IDs to remove. If not provided,
                        all user's group associations are removed.
        responses:
          200:
            content:
              application/json:
                schema: Success
          404:
            content:
              application/json:
                schema: Error
        """

        try:
            association_id = int(association_id)
        except Exception:
            raise ValueError("Invalid association ID")

        data = self.get_json() or {}
        requested_group_ids = data.get("group_ids")

        if (
            requested_group_ids is not None
            and isinstance(requested_group_ids, list)
            and len(requested_group_ids) == 0
        ):
            return self.error("`group_ids` cannot be an empty list", status=400)

        async with self.AsyncSession() as session:
            obj_tag = await session.scalar(
                sa.select(ObjTag)
                .options(selectinload(ObjTag.obj), selectinload(ObjTag.groups))
                .where(ObjTag.id == association_id)
            )

            if not obj_tag:
                return self.error("Association not found", status=404)

            obj_key = obj_tag.obj.internal_key
            is_system_admin = self.current_user.is_system_admin
            current_tag_group_ids = {g.id for g in obj_tag.groups}

            if is_system_admin:
                groups_to_remove = (
                    set(requested_group_ids)
                    if requested_group_ids
                    else current_tag_group_ids
                )
            else:
                user_group_ids = {g.id for g in self.current_user.accessible_groups}
                if requested_group_ids:
                    groups_to_remove = set(requested_group_ids) & user_group_ids
                    if not groups_to_remove:
                        return self.error(
                            "You don't have access to any of the specified groups",
                            status=403,
                        )
                else:
                    groups_to_remove = current_tag_group_ids & user_group_ids

                if not groups_to_remove:
                    return self.error(
                        "You don't have any group associations with this tag to remove",
                        status=403,
                    )

            stmt = GroupObjTag.select(session.user_or_token, mode="delete")
            group_obj_tags = (await session.scalars(
                stmt.where(
                    GroupObjTag.obj_tag_id == association_id,
                    GroupObjTag.group_id.in_(groups_to_remove),
                )
            )).all()
            for group_obj_tag in group_obj_tags:
                await session.delete(group_obj_tag)

            remaining_count = len(current_tag_group_ids) - len(
                groups_to_remove & current_tag_group_ids
            )

            if remaining_count == 0:
                await session.delete(obj_tag)

            await session.commit()
            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": obj_key},
            )
            return self.success(f"Successfully deleted association {association_id}")
