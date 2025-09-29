"""API handlers for managing tags and tag options.

This module provides REST API endpoints for:
- Managing tag options (create, read, update, delete tag options)
- Managing object-tag associations (create, read, delete associations between objects and tags)
"""

import re

from sqlalchemy import func

from baselayer.app.access import auth_or_token, permissions

from ...models import Obj, ObjTag, ObjTagOption
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
        description: Create a new association between an object and a tag option
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
                required:
                  - objtagoption_id
                  - obj_id
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

        if not objtagoption_id or not obj_id:
            return self.error("Both `objtagoption_id` and `obj_id` must be provided")

        with self.Session() as session:
            # Check if association already exists
            if session.scalars(
                ObjTag.select(session.user_or_token)
                .where(ObjTag.objtagoption_id == objtagoption_id)
                .where(ObjTag.obj_id == obj_id)
            ).first():
                return self.error("This tag-obj association already exists")

            # Verify tag exists
            if not session.scalars(
                ObjTagOption.select(session.user_or_token).where(
                    ObjTagOption.id == objtagoption_id
                )
            ).first():
                return self.error("Specified tag does not exist", status=404)

            # Verify obj exists
            if not session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first():
                return self.error("Specified obj does not exist", status=404)

            author_id = self.associated_user_object.id

            new_assoc = ObjTag(
                objtagoption_id=objtagoption_id, obj_id=obj_id, author_id=author_id
            )
            session.add(new_assoc)
            session.commit()
            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": new_assoc.obj.internal_key},
            )
            return self.success(new_assoc)

    @auth_or_token
    def delete(self, association_id):
        """
        ---
        summary: Delete object-tag association
        description: Delete an existing association between an object and a tag option
        tags:
          - object tags
        parameters:
          - in: path
            name: association_id
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
            association_id = int(association_id)
        except Exception:
            raise ValueError("Invalid association ID")

        with self.Session() as session:
            assoc = session.scalars(
                ObjTag.select(session.user_or_token).where(ObjTag.id == association_id)
            ).first()

            if not assoc:
                return self.error("Association not found", status=404)
            obj_key = assoc.obj.internal_key
            session.delete(assoc)
            session.commit()
            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": obj_key},
            )
            return self.success(f"Successfully deleted association {association_id}")
