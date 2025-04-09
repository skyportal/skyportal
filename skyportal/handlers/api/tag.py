
from baselayer.app.access import auth_or_token

from ...models import ObjTagOption, ObjTags
from ..base import BaseHandler


class ObjTagOptionHandler(BaseHandler):
    @auth_or_token
    def get(self):
        # If we wanted to do any query filtering, this is where that would happen
        with self.Session() as session:
            comments = session.scalars(
                ObjTagOption.select(session.user_or_token).columns(ObjTagOption.tag_name)
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
    def put(self):
        pass

    @auth_or_token
    def delete(self):
        pass