import re

from sqlalchemy import func

from baselayer.app.access import auth_or_token

from ...models import Obj, ObjTagOption, ObjTags
from ..base import BaseHandler


class ObjTagOptionHandler(BaseHandler):
    @auth_or_token
    def get(self):
        with self.Session() as session:
            tags = session.scalars(ObjTagOption.select(session.user_or_token)).all()
            return self.success(data=tags)

    @auth_or_token
    def post(self):
        data = self.get_json()
        name = data.get("name")

        if not name or not isinstance(name, str):
            return self.error("`name` must be provided as a non-empty string")

        if not re.fullmatch(r"[A-Za-z0-9]+", name):
            return self.error(
                "`name` must contain only letters and numbers (no spaces, underscores, or special characters)",
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
                    f"Tag '{name}' already exists (case-insensitive match)",
                    status=409,
                )

            new_tag = ObjTagOption(name=name)
            session.add(new_tag)
            session.commit()

            return self.success(new_tag)

    @auth_or_token
    def patch(self, tag_id):
        data = self.get_json()
        new_name = data.get("name")

        if not new_name or not isinstance(new_name, str):
            return self.error("`name` must be provided as a non-empty string")

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
            session.commit()

            return self.success()

    @auth_or_token
    def delete(self, tag_id):
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
    @auth_or_token
    def get(self):
        """Get all tag-obj associations or filter by obj_id/objtagoption_id"""
        obj_id = self.get_query_argument("obj_id", None)
        objtagoption_id = self.get_query_argument("objtagoption_id", None)

        with self.Session() as session:
            query = ObjTags.select(session.user_or_token)

            if obj_id:
                query = query.where(ObjTags.obj_id == obj_id)
            if objtagoption_id:
                query = query.where(ObjTags.objtagoption_id == objtagoption_id)

            associations = session.scalars(query).all()
            return self.success(associations)

    @auth_or_token
    def post(self):
        """Create a new tag-obj association"""
        data = self.get_json()
        objtagoption_id = data.get("objtagoption_id")
        obj_id = data.get("obj_id")

        if not objtagoption_id or not obj_id:
            return self.error("Both `objtagoption_id` and `obj_id` must be provided")

        with self.Session() as session:
            # Check if association already exists
            if session.scalars(
                ObjTags.select(session.user_or_token)
                .where(ObjTags.objtagoption_id == objtagoption_id)
                .where(ObjTags.obj_id == obj_id)
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

            if hasattr(self.current_user, "created_by"):
                author_id = self.current_user.created_by.id
            else:
                author_id = self.current_user.id

            new_assoc = ObjTags(
                objtagoption_id=objtagoption_id, obj_id=obj_id, author_id=author_id
            )
            session.add(new_assoc)
            session.commit()

            return self.success(new_assoc)

    @auth_or_token
    def patch(self, association_id):
        """Update an existing tag-obj association"""
        data = self.get_json()
        new_tag_id = data.get("objtagoption_id")
        new_obj_id = data.get("obj_id")

        if hasattr(self.current_user, "created_by"):
            author_id = self.current_user.created_by.id
        else:
            author_id = self.current_user.id

        if not new_tag_id and not new_obj_id:
            return self.error(
                "Either `objtagoption_id` or `obj_id` has not been provided for update"
            )

        with self.Session() as session:
            assoc = session.scalars(
                ObjTags.select(session.user_or_token).where(
                    ObjTags.id == association_id
                )
            ).first()

            if not assoc:
                return self.error("Association not found", status=404)

            final_tag_id = (
                new_tag_id if new_tag_id is not None else assoc.objtagoption_id
            )
            final_obj_id = new_obj_id if new_obj_id is not None else assoc.obj_id

            existing = session.scalars(
                ObjTags.select(session.user_or_token)
                .where(ObjTags.objtagoption_id == final_tag_id)
                .where(ObjTags.obj_id == final_obj_id)
            ).first()

            if existing:
                return self.error("This tag-obj association already exists", status=409)

            if new_tag_id:
                # Verify new tag exists
                if not session.scalars(
                    ObjTagOption.select(session.user_or_token).where(
                        ObjTagOption.id == new_tag_id
                    )
                ).first():
                    return self.error("Specified tag does not exist", status=404)
                assoc.objtagoption_id = new_tag_id

            if new_obj_id:
                # Verify new obj exists
                if not session.scalars(
                    Obj.select(session.user_or_token).where(Obj.id == new_obj_id)
                ).first():
                    return self.error("Specified obj does not exist", status=404)
                assoc.obj_id = new_obj_id

            assoc.author_id = author_id
            session.commit()
            return self.success()

    @auth_or_token
    def delete(self, association_id):
        """Delete a tag-obj association"""
        with self.Session() as session:
            assoc = session.scalars(
                ObjTags.select(session.user_or_token).where(
                    ObjTags.id == association_id
                )
            ).first()

            if not assoc:
                return self.error("Association not found", status=404)

            session.delete(assoc)
            session.commit()

            return self.success(f"Successfully deleted association {association_id}")
