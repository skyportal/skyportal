from copy import deepcopy
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from .user import add_user_and_setup_groups
from ..base import BaseHandler
from ...models import (
    DBSession,
    Filter,
    Group,
    GroupStream,
    GroupUser,
    Stream,
    User,
    Token,
)


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
                  schema:
                    allOf:
                      - $ref: '#/components/schemas/Success'
                      - type: object
                        properties:
                          data:
                            allOf:
                              - $ref: '#/components/schemas/Group'
                              - type: object
                                properties:
                                  users:
                                    type: array
                                    items:
                                      - $ref: '#/components/schemas/User'
                                    description: List of group users
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all groups
          parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Fetch by name (exact match)
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
                            type: object
                            properties:
                              user_groups:
                                type: array
                                items:
                                  $ref: '#/components/schemas/Group'
                                description: List of groups current user is a member of.
                              all_groups:
                                type: array
                                items:
                                  $ref: '#/components/schemas/Group'
                                description: |
                                  List of all groups user has access to, optionally
                                  including single user groups if specified in request.
            400:
              content:
                application/json:
                  schema: Error
        """
        if group_id is not None:
            if 'Manage groups' in [acl.id for acl in self.current_user.acls]:
                group = (
                    Group.query.options(joinedload(Group.users))
                    .options(joinedload(Group.group_users))
                    .get(group_id)
                )
            else:
                group = Group.query.options(
                    [joinedload(Group.users).load_only(User.id, User.username)]
                ).get(group_id)
                if group is not None and group.id not in [
                    g.id for g in self.current_user.accessible_groups
                ]:
                    return self.error('Insufficient permissions.')
            if group is not None:
                group = group.to_dict()
                # Do not include User.groups to avoid circular reference
                group['users'] = [
                    {'id': user.id, 'username': user.username}
                    for user in group['users']
                ]
                # grab streams:
                streams = (
                    DBSession()
                    .query(Stream)
                    .join(GroupStream)
                    .filter(GroupStream.group_id == group_id)
                    .all()
                )
                group['streams'] = streams
                # grab filters:
                filters = (
                    DBSession().query(Filter).filter(Filter.group_id == group_id).all()
                )
                group['filters'] = filters

                return self.success(data=group)
            return self.error(f"Could not load group with ID {group_id}")
        group_name = self.get_query_argument("name", None)
        if group_name is not None:
            groups = Group.query.filter(Group.name == group_name).all()
            # Ensure access
            if not all(
                [group in self.current_user.accessible_groups for group in groups]
            ):
                return self.error("Insufficient permisisons")
            return self.success(data=groups)

        include_single_user_groups = self.get_query_argument(
            "includeSingleUserGroups", False
        )
        info = {}
        info['user_groups'] = list(self.current_user.groups)
        if (not include_single_user_groups) or (include_single_user_groups == "false"):
            info["all_groups"] = [
                g
                for g in self.current_user.accessible_groups
                if not g.single_user_group
            ]
        else:
            # `accessible_groups` already includes single user groups for sys admins
            if "System admin" in self.current_user.permissions:
                info["all_groups"] = self.current_user.accessible_groups
            else:
                info["all_groups"] = deepcopy(info["user_groups"])
                single_user_groups = Group.query.filter(
                    Group.single_user_group.is_(True)
                ).all()
                info["all_groups"].extend(single_user_groups)
        print(self.request.uri)
        return self.success(data=info)

    @permissions(['Manage groups'])
    def post(self):
        """
        ---
        description: Create a new group
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/GroupNoID'
                  - type: object
                    properties:
                      group_admins:
                        type: array
                        items:
                          type: string
                        description: |
                          List of emails of users to be group admins. Current user will
                          automatically be added as a group admin.
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
                          type: object
                          properties:
                            id:
                              type: integer
                              description: New group ID
        """
        data = self.get_json()

        group_admin_emails = [
            e.strip() for e in data.get('group_admins', []) if e.strip()
        ]
        group_admins = list(User.query.filter(User.username.in_(group_admin_emails)))
        if self.current_user not in group_admins and not isinstance(
            self.current_user, Token
        ):
            group_admins.append(self.current_user)

        g = Group(name=data['name'])
        DBSession().add(g)
        DBSession().flush()
        DBSession().add_all(
            [GroupUser(group=g, user=user, admin=True) for user in group_admins]
        )
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
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
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

        self.push_all(
            action='skyportal/REFRESH_GROUP', payload={'group_id': int(group_id)}
        )
        self.push_all(action='skyportal/FETCH_GROUPS')
        return self.success()


class GroupUserHandler(BaseHandler):
    @permissions(['Manage groups'])
    def post(self, group_id, *ignored_args):
        """
        ---
        description: Add a group user
        parameters:
          - in: path
            name: group_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  username:
                    type: string
                  admin:
                    type: boolean
                required:
                  - username
                  - admin
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
                          type: object
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

        username = data.pop("username", None)
        if username is None:
            return self.error("Username must be specified")

        admin = data.pop("admin", False)
        group_id = int(group_id)
        group = Group.query.get(group_id)
        if group.single_user_group:
            return self.error("Cannot add users to single-user groups.")
        user = User.query.filter(User.username == username.lower()).first()
        if user is None:
            user_id = add_user_and_setup_groups(
                username=username,
                roles=["Full user"],
                group_ids_and_admin=[[group_id, admin]],
            )
        else:
            user_id = user.id
            # Just add new GroupUser
            gu = (
                GroupUser.query.filter(GroupUser.group_id == group_id)
                .filter(GroupUser.user_id == user_id)
                .first()
            )
            if gu is None:
                DBSession.add(
                    GroupUser(group_id=group_id, user_id=user_id, admin=admin)
                )
            else:
                return self.error(
                    "Specified user is already associated with this group."
                )
        DBSession().commit()

        self.push_all(action='skyportal/REFRESH_GROUP', payload={'group_id': group_id})
        return self.success(
            data={'group_id': group_id, 'user_id': user_id, 'admin': admin}
        )

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
        group = Group.query.get(group_id)
        if group.single_user_group:
            return self.error("Cannot delete users from single user groups.")
        user_id = User.query.filter(User.username == username).first().id
        (
            GroupUser.query.filter(GroupUser.group_id == group_id)
            .filter(GroupUser.user_id == user_id)
            .delete()
        )
        DBSession().commit()
        self.push_all(
            action='skyportal/REFRESH_GROUP', payload={'group_id': int(group_id)}
        )
        return self.success()


class GroupStreamHandler(BaseHandler):
    @permissions(['System admin'])
    def post(self, group_id, *ignored_args):
        """
        ---
        description: Add alert stream access to group
        parameters:
          - in: path
            name: group_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  stream_id:
                    type: integer
                required:
                  - stream_id
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
                          type: object
                          properties:
                            group_id:
                              type: integer
                              description: Group ID
                            stream_id:
                              type: integer
                              description: Stream ID
        """
        data = self.get_json()
        group_id = int(group_id)
        # group = Group.query.filter(Group.id == group_id).first()
        group = (
            Group.query.options(joinedload(Group.users))
            .options(joinedload(Group.group_users))
            .get(group_id)
        )
        if group is None:
            return self.error("Specified group_id does not exist.")
        stream_id = data.get('stream_id')
        stream = Stream.query.filter(Stream.id == stream_id).first()
        if stream is None:
            return self.error("Specified stream_id does not exist.")
        else:
            # todo: ensure all current group users have access to this stream
            for user in group.users:
                # get single user group
                single_user_group = Group.query.filter(  # noqa
                    Group.name == user.username
                ).first()
                # todo: do the check

            # Add new GroupStream
            gs = GroupStream.query.filter(
                GroupStream.group_id == group_id, GroupStream.stream_id == stream_id
            ).first()
            if gs is None:
                DBSession.add(GroupStream(group_id=group_id, stream_id=stream_id))
            else:
                return self.error(
                    "Specified stream is already associated with this group."
                )
        DBSession().commit()

        self.push_all(action='skyportal/REFRESH_GROUP', payload={'group_id': group_id})
        return self.success(data={'group_id': group_id, 'stream_id': stream_id})

    @permissions(['System admin'])
    def delete(self, group_id, stream_id):
        """
        ---
        description: Delete an alert stream from group
        parameters:
          - in: path
            name: group_id
            required: true
            schema:
              type: integer
          - in: path
            name: stream_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        stream = Stream.query.filter(Stream.id == int(stream_id)).first()
        stream_id = stream.id
        if stream is None:
            return self.error("Specified stream_id does not exist.")
        else:
            (
                GroupStream.query.filter(GroupStream.group_id == group_id)
                .filter(GroupStream.stream_id == stream_id)
                .delete()
            )
            DBSession().commit()
            self.push_all(
                action='skyportal/REFRESH_GROUP', payload={'group_id': int(group_id)}
            )
            return self.success()
