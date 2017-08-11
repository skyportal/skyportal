import tornado.web
from baselayer.app.access import permissions
from baselayer.app.handlers.base import BaseHandler
from ..models import DBSession, Group


class GroupHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, group_id=None):
        if group_id is not None:
            info = Group.get_if_owned_by(group_id, self.current_user)
        else:
            info = list(self.current_user.groups)

        if info is None:
            return self.error(f"Could not load group {group_id}",
                              {"group_id": group_id})
        else:
            return self.success(info)

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
