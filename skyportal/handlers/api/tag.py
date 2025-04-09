
from baselayer.app.access import auth_or_token

from ...models import ObjTagOption, ObjTags
from ..base import BaseHandler


class ObjTagOptionHandler(BaseHandler):
    @auth_or_token
    def get(self):
        data = self.get_json()
        with self.Session() as session:
            comments = session.scalars(
                ObjTagOption.select(session.user_or_token).with_only_columns(ObjTagOption.tag_name)
            ).all()
            return self.success(data=comments)

    @auth_or_token
    def post(self):
        data = self.get_json()
        tag_text = data.get("tag_name")
        
        if not tag_text or not isinstance(tag_text, str):
            return self.error("`tag_name` must be provided as a non-empty string")
            
        with self.Session() as session:
            if session.scalars(ObjTagOption.select(session.user_or_token).where(ObjTagOption.tag_name == tag_text)).first():
                return self.error("Tag already exists")
                
            new_tag = ObjTagOption(tag_name=tag_text)
            session.add(new_tag)
            session.commit()
            
            return self.success(data={"id": new_tag.id, "tag_name": new_tag.tag_name})
    
    @auth_or_token
    def put(self, tag_id):
        data = self.get_json()
        new_tag_name = data.get('tag_name')

        if not new_tag_name or not isinstance(new_tag_name, str):
            return self.error("`tag_name` must be provided as a non-empty string")

        with self.Session() as session:
            tag = session.scalars(
                ObjTagOption.select(session.user_or_token).where(ObjTagOption.id == tag_id)
            ).first()
            
            if not tag:
                return self.error("Tag not found", status=404)

            # Vérifie que le nouveau nom n'est pas déjà utilisé
            if session.scalars(
                ObjTagOption.select(session.user_or_token)
                .where(ObjTagOption.tag_name == new_tag_name)
                .where(ObjTagOption.id != tag_id)
            ).first():
                return self.error("This tag name already exists for another tag")

            # Met à jour le tag
            tag.tag_name = new_tag_name
            session.commit()
            
            return self.success(data={"id": tag.id, "tag_name": tag.tag_name})

    @auth_or_token
    def delete(self, tag_id):
        with self.Session() as session:
            tag = session.scalars(
                ObjTagOption.select(session.user_or_token).where(ObjTagOption.id == tag_id)
            ).first()

            if not tag:
                return self.error("Tag not found", status=404)

            session.delete(tag)
            session.commit()
            
            return self.success(f"Successfully deleted tag {tag}")