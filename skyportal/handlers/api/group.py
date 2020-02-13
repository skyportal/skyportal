import tornado.web
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Group, GroupUser, User, Token, Source


class GroupHandler(BaseHandler):
    @auth_or_token
    def get(self, group_id=None):
        """
        ---
        single:
          description: Retrieve a group
          parameters:
            - in: path
              name: group_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleGroup
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all groups
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfGroups
            400:
              content:
                application/json:
                  schema: Error
        """
        info = {}
        if group_id is not None:
            if 'Manage groups' in [acl.id for acl in self.current_user.acls]:
                group = Group.query.options(joinedload(Group.users)).options(
                    joinedload(Group.group_users)).options(
                        joinedload(Group.sources)).get(group_id)
            else:
                group = Group.query.options([
                    joinedload(Group.users).load_only(User.id, User.username),
                    joinedload(Group.sources)]).get(group_id)
                if group is not None and group.id not in [
                        g.id for g in self.current_user.groups]:
                    return self.error('Insufficient permissions.')
            info['group'] = group
        else:
            info['user_groups'] = list(self.current_user.groups)
            info['all_groups'] = (list(Group.query) if hasattr(self.current_user, 'roles')
                                  and 'Super admin' in
                                  [role.id for role in self.current_user.roles]
                                  else None)
            return self.success(data=info)
        if 'group' in info:
            if info['group'] is not None:
                info['group'] = info['group'].to_dict()
                # Do not include User.groups to avoid circular reference
                info['group']['users'] = [{'id': user.id, 'username': user.username}
                                          for user in info['group']['users']]
                return self.success(data=info)
            else:
                return self.error(f"Could not load group {group_id}",
                                  data={"group_id": group_id})

    @permissions(['Manage groups'])
    def post(self):
        """
        ---
        description: Create a new group
        requestBody:
          content:
            application/json:
              schema: GroupNoID
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        id:
                          type: integer
                          description: New group ID
        """
        data = self.get_json()

        group_admin_emails = [e.strip() for e in data.get('group_admins', [])
                              if e.strip()]
        group_admins = list(User.query.filter(User.username.in_(
            group_admin_emails)))
        if self.current_user not in group_admins and not isinstance(self.current_user, Token):
            group_admins.append(self.current_user)

        source_ids = [s.strip() for s in data.get('source_ids', []) if s.strip()]
        sources = list(Source.query.filter(Source.id.in_(source_ids)))

        g = Group(name=data['name'], sources=sources)
        DBSession().add_all(
            [GroupUser(group=g, user=user, admin=True) for user in group_admins])
        DBSession().commit()

        self.push_all(action='skyportal/FETCH_GROUPS')
        return self.success(data={"id": g.id})

    @permissions(['Manage groups'])
    def put(self, group_id):
        """
        ---
        description: Update a group
        parameters:
          - in: path
            name: group_id
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: GroupNoID
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
        data = self.get_json()
        data['id'] = group_id

        schema = Group.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()

        return self.success(action='skyportal/FETCH_GROUPS')

    @permissions(['Manage groups'])
    def delete(self, group_id):
        """
        ---
        description: Delete a group
        parameters:
          - in: path
            name: group_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        g = Group.query.get(group_id)
        DBSession().delete(g)
        DBSession().commit()

        self.push_all(action='skyportal/REFRESH_GROUP', payload={'group_id': int(group_id)})
        self.push_all(action='skyportal/FETCH_GROUPS')
        return self.success()


class GroupUserHandler(BaseHandler):
    @permissions(['Manage groups'])
    def post(self, group_id, username):
        """
        ---
        description: Add a group user
        parameters:
          - in: path
            name: group_id
            required: true
            schema:
              type: integer
          - in: path
            name: username
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  admin:
                    type: boolean
                required:
                  - admin
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        group_id:
                          type: integer
                          description: Group ID
                        user_id:
                          type: integer
                          description: User ID
                        admin:
                          type: boolean
                          description: Boolean indicating whether user is group admin
        """
        data = self.get_json()
        try:
            user_id = User.query.filter(User.username == username).first().id
        except AttributeError:
            return self.error('Invalid username.')
        gu = (GroupUser.query.filter(GroupUser.group_id == group_id)
                       .filter(GroupUser.user_id == user_id).first())
        if gu is None:
            gu = GroupUser(group_id=group_id, user_id=user_id)
        gu.admin = data['admin']
        DBSession().add(gu)
        DBSession().commit()

        self.push_all(action='skyportal/REFRESH_GROUP',
                      payload={'group_id': gu.group_id})
        return self.success(data={'group_id': gu.group_id, 'user_id': gu.user_id,
                                  'admin': gu.admin})

    @permissions(['Manage groups'])
    def delete(self, group_id, username):
        """
        ---
        description: Delete a group user
        parameters:
          - in: path
            name: group_id
            required: true
            schema:
              type: integer
          - in: path
            name: username
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        user_id = User.query.filter(User.username == username).first().id
        (GroupUser.query.filter(GroupUser.group_id == group_id)
                   .filter(GroupUser.user_id == user_id).delete())
        DBSession().commit()
        self.push_all(action='skyportal/REFRESH_GROUP',
                      payload={'group_id': int(group_id)})
        return self.success()
