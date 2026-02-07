"""API handlers for managing tags and tag options.

This module provides REST API endpoints for:
- Managing tag options (create, read, update, delete tag options)
- Managing object-tag associations (create, read, delete associations between objects and tags)
"""

import re

import sqlalchemy as sa
from sqlalchemy import func

from baselayer.app.access import auth_or_token, permissions

from ...models import Group, GroupObjTag, Obj, ObjTag, ObjTagOption
from ..base import BaseHandler


class ObjTagOptionHandler(BaseHandler):
    """Handler for managing tag options.

    Tag options define the available tags that can be applied to objects.
    They include a name and optional color for display purposes.
    """

    @auth_or_token
    def get(self):
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
        with self.Session() as session:
            tags = session.scalars(ObjTagOption.select(session.user_or_token)).all()
            return self.success(data=tags)

    @permissions(["Manage sources"])
    def post(self):
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

        with self.Session() as session:
            existing_tag = session.scalars(
                ObjTagOption.select(session.user_or_token).where(
                    func.lower(ObjTagOption.name) == name.lower()
                )
            ).first()

            if existing_tag:
                return self.error(
                    f"Tag '{name}' already exists as '{existing_tag.name}' (case-insensitive match)",
                    status=409,
                )

            new_tag = ObjTagOption(name=name, color=color)
            session.add(new_tag)
            session.commit()

            return self.success(new_tag)

    @auth_or_token
    def patch(self, tag_id):
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

        with self.Session() as session:
            tag = session.scalars(
                ObjTagOption.select(session.user_or_token).where(
                    ObjTagOption.id == tag_id
                )
            ).first()

            if not tag:
                return self.error("Tag not found", status=404)

            if session.scalars(
                ObjTagOption.select(session.user_or_token)
                .where(ObjTagOption.name == new_name)
                .where(ObjTagOption.id != tag_id)
            ).first():
                return self.error("This tag name already exists for another tag")

            tag.name = new_name
            if new_color:
                tag.color = new_color
            session.commit()

            return self.success()

    @permissions(["Manage sources"])
    def delete(self, tag_id):
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

        with self.Session() as session:
            tag = session.scalars(
                ObjTagOption.select(session.user_or_token).where(
                    ObjTagOption.id == tag_id
                )
            ).first()

            if not tag:
                return self.error("Tag not found", status=404)

            session.delete(tag)
            session.commit()

            return self.success(f"Successfully deleted tag {tag}")


class ObjTagHandler(BaseHandler):
    """Handler for managing object-tag associations.

    Manages the relationships between objects and tag options,
    allowing objects to be tagged with specific labels.
    """

    @auth_or_token
    def get(self):
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
        objtagoption_id = self.get_query_argument("objtagoption_id", None)

        with self.Session() as session:
            query = ObjTag.select(session.user_or_token)

            if obj_id:
                query = query.where(ObjTag.obj_id == obj_id)
            if objtagoption_id:
                query = query.where(ObjTag.objtagoption_id == objtagoption_id)

            associations = session.scalars(query).all()
            return self.success(associations)

    @auth_or_token
    def post(self):
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
        group_ids = data.get("group_ids", [])

        if not objtagoption_id or not obj_id:
            return self.error("Both `objtagoption_id` and `obj_id` must be provided")

        if not group_ids or not isinstance(group_ids, list) or len(group_ids) == 0:
            return self.error("`group_ids` must be provided as a non-empty list")

        with self.Session() as session:
            # Verify tag option exists
            if not session.scalar(
                sa.select(ObjTagOption.id).where(ObjTagOption.id == objtagoption_id)
            ):
                return self.error("Specified tag option does not exist", status=404)

            # Verify obj exists
            obj = session.scalars(sa.select(Obj).where(Obj.id == obj_id)).first()
            if not obj:
                return self.error("Specified obj does not exist", status=404)

            # System admins can add tags to any group
            requested_group_ids = set(group_ids)
            if self.current_user.is_system_admin:
                existing_group_ids = set(
                    session.scalars(
                        sa.select(Group.id).where(Group.id.in_(requested_group_ids))
                    ).all()
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
            existing_assoc_id = session.scalar(
                sa.select(ObjTag.id)
                .where(ObjTag.objtagoption_id == objtagoption_id)
                .where(ObjTag.obj_id == obj_id)
            )

            if existing_assoc_id:
                existing_group_ids = set(
                    session.scalars(
                        sa.select(GroupObjTag.group_id).where(
                            GroupObjTag.obj_tag_id == existing_assoc_id
                        )
                    ).all()
                )

                groups_to_add = valid_group_ids - existing_group_ids

                if not groups_to_add:
                    return self.error(
                        "This tag is already associated with all the selected groups",
                        status=400,
                    )

                for group_id in groups_to_add:
                    group_obj_tag = GroupObjTag(
                        group_id=group_id,
                        obj_tag_id=existing_assoc_id,
                    )
                    session.add(group_obj_tag)
                session.commit()

                self.push_all(
                    action="skyportal/REFRESH_SOURCE",
                    payload={"obj_key": obj.internal_key},
                )
                return self.success(
                    {"id": existing_assoc_id, "message": "Groups added to existing tag"}
                )

            groups = session.scalars(
                sa.select(Group).where(Group.id.in_(valid_group_ids))
            ).all()

            new_assoc = ObjTag(
                objtagoption_id=objtagoption_id,
                obj_id=obj_id,
                author_id=self.associated_user_object.id,
            )
            new_assoc.groups = groups
            session.add(new_assoc)
            session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": obj.internal_key},
            )
            return self.success(new_assoc)

    @auth_or_token
    def delete(self, association_id):
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

        with self.Session() as session:
            obj_tag = session.scalars(
                sa.select(ObjTag).where(ObjTag.id == association_id)
            ).first()

            if not obj_tag:
                return self.error("Association not found", status=404)

            obj_key = obj_tag.obj.internal_key
            is_system_admin = self.current_user.is_system_admin
            current_tag_group_ids = {g.id for g in obj_tag.groups}

            if is_system_admin:
                if requested_group_ids:
                    groups_to_remove = set(requested_group_ids)
                else:
                    groups_to_remove = current_tag_group_ids

                for group_id in groups_to_remove:
                    group_obj_tag = session.scalars(
                        sa.select(GroupObjTag).where(
                            GroupObjTag.obj_tag_id == association_id,
                            GroupObjTag.group_id == group_id,
                        )
                    ).first()
                    if group_obj_tag:
                        session.delete(group_obj_tag)

                remaining_count = len(current_tag_group_ids) - len(
                    groups_to_remove & current_tag_group_ids
                )

                if remaining_count == 0:
                    session.delete(obj_tag)

                session.commit()
                self.push_all(
                    action="skyportal/REFRESH_SOURCE",
                    payload={"obj_key": obj_key},
                )
                return self.success(f"Successfully deleted tag {association_id}")

            # For non-admin users, only remove their group associations
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

            for group_id in groups_to_remove:
                group_obj_tag = session.scalars(
                    sa.select(GroupObjTag).where(
                        GroupObjTag.obj_tag_id == association_id,
                        GroupObjTag.group_id == group_id,
                    )
                ).first()
                if group_obj_tag:
                    session.delete(group_obj_tag)

            remaining_count = len(current_tag_group_ids) - len(
                groups_to_remove & current_tag_group_ids
            )

            if remaining_count == 0:
                session.delete(obj_tag)

            session.commit()
            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": obj_key},
            )
            return self.success(f"Successfully deleted association {association_id}")
