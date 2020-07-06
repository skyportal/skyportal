import base64
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Group, Classification


class ClassificationHandler(BaseHandler):
    @auth_or_token
    def get(self, classification_id):
        """
        ---
        description: Retrieve a classification
        parameters:
          - in: path
            name: classification_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: SingleClassification
          400:
            content:
              application/json:
                schema: Error
        """
        classification = Classification.get_if_owned_by(
                               classification_id, self.current_user
                         )
        if classification is None:
            return self.error('Invalid classification ID.')
        return self.success(data=classification)

    @permissions(['Classify'])
    def post(self):
        """
        ---
        description: Post a classification
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  obj_id:
                    type: string
                  classification:
                    type: string
                  taxonomy:
                    type: integer
                  probability:
                    type: float
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups should be
                      able to view classification. Defaults to all of
                      requesting user's groups.
                required:
                  - obj_id
                  - classification
                  - taxonomy
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
                            comment_id:
                              type: integer
                              description: New classification ID
        """
        data = self.get_json()
        obj_id = data['obj_id']
        # Ensure user/token has access to parent source
        _ = Source.get_obj_if_owned_by(obj_id, self.current_user)
        user_group_ids = [g.id for g in self.current_user.groups]
        group_ids = data.pop("group_ids", user_group_ids)
        group_ids = [gid for gid in group_ids if gid in user_group_ids]
        if not group_ids:
            return self.error(f"Invalid group IDs field ({group_ids}): "
                              "You must provide one or more valid group IDs.")
        groups = Group.query.filter(Group.id.in_(group_ids)).all()

        author = self.associated_user_object.username
        classification = Classification(classification=data['classification'],
                          obj_id=obj_id, probability=data.get('probability'),
                          taxonomy=data["taxonomy"],
                          author=author, groups=groups)

        DBSession().add(classification)
        DBSession().commit()

        self.push_all(action='skyportal/REFRESH_SOURCE',
                      payload={'obj_id': comment.obj_id})
        return self.success(data={'classification_id': classification.id})

    @permissions(['Classify'])
    def put(self, classification_id):
        """
        ---
        description: Update a classification
        parameters:
          - in: path
            name: classification
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ClassificationNoID'
                  - type: object
                    properties:
                      group_ids:
                        type: array
                        items:
                          type: integer
                        description: |
                          List of group IDs corresponding to which groups should be
                          able to view classification.
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
        c = Classification.get_if_owned_by(classification_id, self.current_user)
        if c is None:
            return self.error('Invalid classification ID.')

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        data['id'] = comment_id

        schema = Comment.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().flush()
        if group_ids is not None:
            c = Classification.get_if_owned_by(classification_id, self.current_user)
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if not groups:
                return self.error("Invalid group_ids field. "
                                  "Specify at least one valid group ID.")
            if "Super admin" not in [r.id for r in self.associated_user_object.roles]:
                if not all([group in self.current_user.groups for group in groups]):
                    return self.error("Cannot associate comment with groups you are "
                                      "not a member of.")
            c.groups = groups
        DBSession().commit()
        self.push_all(action='skyportal/REFRESH_SOURCE',
                      payload={'obj_id': c.obj_id})
        return self.success()

    @permissions(['Classify'])
    def delete(self, comment_id):
        """
        ---
        description: Delete a classification
        parameters:
          - in: path
            name: classification_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        user = self.associated_user_object.username
        roles = (self.current_user.roles if hasattr(self.current_user, 'roles') else [])
        c = Classification.query.get(classification_id)
        if c is None:
            return self.error("Invalid comment ID")
        obj_id = c.obj_id
        author = c.author
        if ("Super admin" in [role.id for role in roles]) or (user == author):
            Classification.query.filter_by(id=comment_id).delete()
            DBSession().commit()
        else:
            return self.error('Insufficient user permissions.')
        self.push_all(action='skyportal/REFRESH_SOURCE',
                      payload={'obj_id': obj_id})
        return self.success()


class CommentAttachmentHandler(BaseHandler):
    @auth_or_token
    def get(self, comment_id):
        """
        ---
        description: Download comment attachment
        parameters:
          - in: path
            name: comment_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application:
                schema:
                  type: string
                  format: base64
                  description: base64-encoded contents of attachment
        """
        comment = Comment.get_if_owned_by(comment_id, self.current_user)
        if comment is None:
            return self.error('Invalid comment ID.')
        self.set_header(
            "Content-Disposition", "attachment; "
            f"filename={comment.attachment_name}")
        self.set_header("Content-type", "application/octet-stream")
        self.write(base64.b64decode(comment.attachment_bytes))
