import tornado.web
from sqlalchemy.orm import joinedload
from baselayer.app.access import permissions
from baselayer.app.handlers.base import BaseHandler
from ..models import DBSession, Group, GroupUser


class GroupHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, group_id=None):
        if group_id is not None:
            info = Group.get_if_owned_by(group_id, self.current_user,
                                         options=joinedload(Group.users))
        else:
            info = list(self.current_user.groups)

        if info is not None:
            return self.success(info)
        else:
            return self.error(f"Could not load group {group_id}",
                              {"group_id": group_id})

    @permissions(['Manage groups'])
    def post(self):
        data = self.get_json()

        g = Group(name=data['groupName'])
        DBSession().add(g)
        DBSession().commit()

        return self.success({"id": g.id}, 'cesium/FETCH_GROUPS')

    @permissions(['Manage groups'])
    def put(self, group_id):
        data = self.get_json()

        g = Group.query.get(group_id)
        g.name = data['groupName']
        DBSession().commit()

        return self.success(action='cesium/FETCH_GROUPS')

    @permissions(['Manage groups'])
    def delete(self, group_id):
        g = Group.query.get(group_id)
        DBSession().delete(g)
        DBSession().commit()

        return self.success(action='cesium/FETCH_GROUPS')


class GroupUserHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        data = self.get_json()
        gu = GroupUser(group_id=data['groupID'], user_id=data['userID'],
                       admin=data['admin'])
        DBSession().add(gu)
        DBSession().commit()

    @tornado.web.authenticated
    def delete(self, group_id, user_id):
        data = self.get_json()
        GroupUser.query.filter(GroupUser.group_id == group_id)\
                       .filter(GroupUser.user_id == user_id).delete()
        DBSession().commit()
