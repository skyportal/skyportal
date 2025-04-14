from baselayer.app.access import auth_or_token

from ...models import ObjTagOption, ObjTags, Source
from ..base import BaseHandler


class ObjTagOptionHandler(BaseHandler):
    @auth_or_token
    def get(self, tag_identifier=None):
        with self.Session() as session:
            if tag_identifier is None:
                tags = session.scalars(ObjTagOption.select(session.user_or_token)).all()

                return self.success(
                    data=[{"id": tag.id, "tag_name": tag.tag_name} for tag in tags]
                )

            elif tag_identifier.isdigit():
                tag = session.scalars(
                    ObjTagOption.select(session.user_or_token).where(
                        ObjTagOption.id == int(tag_identifier)
                    )
                ).first()

                if tag is None:
                    return self.error(
                        f"Tag with ID {tag_identifier} not found", status=404
                    )

                return self.success(data={"id": tag.id, "tag_name": tag.tag_name})

            elif isinstance(tag_identifier, str):
                tag = session.scalars(
                    ObjTagOption.select(session.user_or_token).where(
                        ObjTagOption.tag_name == tag_identifier
                    )
                ).first()

                if tag is None:
                    return self.error(
                        f"Tag with name '{tag_identifier}' not found", status=404
                    )

                return self.success(data={"id": tag.id, "tag_name": tag.tag_name})

    @auth_or_token
    def post(self):
        data = self.get_json()
        tag_text = data.get("tag_name")

        if not tag_text or not isinstance(tag_text, str):
            return self.error("`tag_name` must be provided as a non-empty string")

        with self.Session() as session:
            if session.scalars(
                ObjTagOption.select(session.user_or_token).where(
                    ObjTagOption.tag_name == tag_text
                )
            ).first():
                return self.error("Tag already exists", status=404)

            new_tag = ObjTagOption(tag_name=tag_text)
            session.add(new_tag)
            session.commit()

            return self.success(data={"id": new_tag.id, "tag_name": new_tag.tag_name})

    @auth_or_token
    def put(self, tag_id):
        data = self.get_json()
        new_tag_name = data.get("tag_name")

        if not new_tag_name or not isinstance(new_tag_name, str):
            return self.error("`tag_name` must be provided as a non-empty string")

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
                .where(ObjTagOption.tag_name == new_tag_name)
                .where(ObjTagOption.id != tag_id)
            ).first():
                return self.error("This tag name already exists for another tag")

            tag.tag_name = new_tag_name
            session.commit()

            return self.success(data={"id": tag.id, "tag_name": tag.tag_name})

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
        """Get all tag-source associations or filter by source_id/objtagoption_id"""
        source_id = self.get_query_argument("source_id", None)
        objtagoption_id = self.get_query_argument("objtagoption_id", None)

        with self.Session() as session:
            query = ObjTags.select(session.user_or_token)

            if source_id:
                query = query.where(ObjTags.source_id == source_id)
            if objtagoption_id:
                query = query.where(ObjTags.objtagoption_id == objtagoption_id)

            associations = session.scalars(query).all()
            return self.success(
                data=[
                    {
                        "id": a.id,
                        "objtagoption_id": a.objtagoption_id,
                        "source_id": a.source_id,
                    }
                    for a in associations
                ]
            )

    @auth_or_token
    def post(self):
        """Create a new tag-source association"""
        data = self.get_json()
        objtagoption_id = data.get("objtagoption_id")
        source_id = data.get("source_id")

        if not objtagoption_id or not source_id:
            return self.error("Both `objtagoption_id` and `source_id` must be provided")

        with self.Session() as session:
            # Check if association already exists
            if session.scalars(
                ObjTags.select(session.user_or_token)
                .where(ObjTags.objtagoption_id == objtagoption_id)
                .where(ObjTags.source_id == source_id)
            ).first():
                return self.error("This tag-source association already exists")

            # Verify tag exists
            if not session.scalars(
                ObjTagOption.select(session.user_or_token).where(
                    ObjTagOption.id == objtagoption_id
                )
            ).first():
                return self.error("Specified tag does not exist", status=404)

            # Verify source exists
            if not session.scalars(
                Source.select(session.user_or_token).where(Source.id == source_id)
            ).first():
                return self.error("Specified source does not exist", status=404)

            new_assoc = ObjTags(objtagoption_id=objtagoption_id, source_id=source_id)
            session.add(new_assoc)
            session.commit()

            return self.success(
                data={
                    "id": new_assoc.id,
                    "objtagoption_id": new_assoc.objtagoption_id,
                    "source_id": new_assoc.source_id,
                }
            )

    @auth_or_token
    def put(self, association_id):
        """Update an existing tag-source association"""
        data = self.get_json()
        new_tag_id = data.get("objtagoption_id")
        new_source_id = data.get("source_id")

        if not new_tag_id and not new_source_id:
            return self.error(
                "Either `objtagoption_id` or `source_id` has not been provided for update"
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
            final_source_id = (
                new_source_id if new_source_id is not None else assoc.source_id
            )

            existing = session.scalars(
                ObjTags.select(session.user_or_token)
                .where(ObjTags.objtagoption_id == final_tag_id)
                .where(ObjTags.source_id == final_source_id)
            ).first()

            if existing:
                return self.error(
                    "This tag-source association already exists", status=409
                )

            if new_tag_id:
                # Verify new tag exists
                if not session.scalars(
                    ObjTagOption.select(session.user_or_token).where(
                        ObjTagOption.id == new_tag_id
                    )
                ).first():
                    return self.error("Specified tag does not exist", status=404)
                assoc.objtagoption_id = new_tag_id

            if new_source_id:
                # Verify new source exists
                if not session.scalars(
                    Source.select(session.user_or_token).where(
                        Source.id == new_source_id
                    )
                ).first():
                    return self.error("Specified source does not exist", status=404)
                assoc.source_id = new_source_id

            session.commit()
            return self.success(
                data={
                    "id": assoc.id,
                    "objtagoption_id": assoc.objtagoption_id,
                    "source_id": assoc.source_id,
                }
            )

    @auth_or_token
    def delete(self, association_id):
        """Delete a tag-source association"""
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
