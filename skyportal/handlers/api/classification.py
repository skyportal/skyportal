from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Group, Classification, Taxonomy
from .internal.recent_sources import RecentSourcesHandler
from .internal.source_views import SourceViewsHandler


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
                  taxonomy_id:
                    type: integer
                  probability:
                    type: float
                    nullable: true
                    minimum: 0.0
                    maximum: 1.0
                    description: |
                      User-assigned probability of this classification on this
                      taxonomy. If multiple classifications are given for the
                      same source by the same user, the sum of the
                      classifications ought to equal unity. Only individual
                      probabilities are checked.
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
                  - taxonomy_id
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
                            classification_id:
                              type: integer
                              description: New classification ID
        """
        data = self.get_json()
        obj_id = data['obj_id']
        # Ensure user/token has access to parent source
        source = Source.get_obj_if_owned_by(obj_id, self.current_user)
        if source is None:
            return self.error("Invalid source.")
        user_group_ids = [g.id for g in self.current_user.groups]
        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
        group_ids = data.pop("group_ids", user_group_ids)
        group_ids = [gid for gid in group_ids if gid in user_accessible_group_ids]
        if not group_ids:
            return self.error(
                f"Invalid group IDs field ({group_ids}): "
                "You must provide one or more valid group IDs."
            )
        groups = Group.query.filter(Group.id.in_(group_ids)).all()

        author = self.associated_user_object

        # check the taxonomy
        taxonomy_id = data["taxonomy_id"]
        taxonomy = Taxonomy.get_taxonomy_usable_by_user(taxonomy_id, self.current_user)
        if len(taxonomy) == 0:
            return self.error(
                'That taxonomy does not exist or is not available to user.'
            )
        if not isinstance(taxonomy, list):
            return self.error('Problem retrieving taxonomy')

        def allowed_classes(hierarchy):
            if "class" in hierarchy:
                yield hierarchy["class"]

            if "subclasses" in hierarchy:
                for item in hierarchy.get("subclasses", []):
                    yield from allowed_classes(item)

        if data['classification'] not in allowed_classes(taxonomy[0].hierarchy):
            return self.error(
                f"That classification ({data['classification']}) "
                'is not in the allowed classes for the chosen '
                f'taxonomy (id={taxonomy_id}'
            )

        probability = data.get('probability')
        if probability is not None:
            if probability < 0 or probability > 1:
                return self.error(
                    f"That probability ({probability}) is outside "
                    "the allowable range (0-1)."
                )

        classification = Classification(
            classification=data['classification'],
            obj_id=obj_id,
            probability=probability,
            taxonomy_id=data["taxonomy_id"],
            author=author,
            author_name=author.username,
            groups=groups,
        )

        DBSession().add(classification)
        DBSession().commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': classification.obj.internal_key},
        )
        if classification.obj_id in RecentSourcesHandler.get_recent_source_ids(
            self.current_user
        ):
            self.push_all(action='skyportal/FETCH_RECENT_SOURCES')

        if classification.obj_id in map(
            lambda view_obj_tuple: view_obj_tuple[1],
            SourceViewsHandler.get_top_source_views_and_ids(self.current_user),
        ):
            self.push_all(action='skyportal/FETCH_TOP_SOURCES')

        self.push_all(
            action='skyportal/REFRESH_CANDIDATE',
            payload={'id': classification.obj.internal_key},
        )

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
        data['id'] = classification_id

        schema = Classification.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        DBSession().flush()
        if group_ids is not None:
            c = Classification.get_if_owned_by(classification_id, self.current_user)
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if not groups:
                return self.error(
                    "Invalid group_ids field. " "Specify at least one valid group ID."
                )
            if not all(
                [group in self.current_user.accessible_groups for group in groups]
            ):
                return self.error(
                    "Cannot associate classification with groups you are "
                    "not a member of."
                )
            c.groups = groups
        DBSession().commit()
        self.push_all(
            action='skyportal/REFRESH_SOURCE', payload={'obj_key': c.obj.internal_key},
        )
        self.push_all(
            action='skyportal/REFRESH_CANDIDATE', payload={'id': c.obj.internal_key},
        )
        if c.obj_id in RecentSourcesHandler.get_recent_source_ids(self.current_user):
            self.push_all(action='skyportal/FETCH_RECENT_SOURCES')

        return self.success()

    @permissions(['Classify'])
    def delete(self, classification_id):
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
        user = self.associated_user_object
        roles = self.current_user.roles if hasattr(self.current_user, 'roles') else []
        c = Classification.query.get(classification_id)
        if c is None:
            return self.error("Invalid classification ID")
        obj_id = c.obj_id
        obj_key = c.obj.internal_key
        author = c.author
        if ("Super admin" in [role.id for role in roles]) or (user.id == author.id):
            Classification.query.filter_by(id=classification_id).delete()
            DBSession().commit()
        else:
            return self.error('Insufficient user permissions.')
        self.push_all(
            action='skyportal/REFRESH_SOURCE', payload={'obj_key': obj_key},
        )
        self.push_all(
            action='skyportal/REFRESH_CANDIDATE', payload={'id': obj_key},
        )
        if obj_id in RecentSourcesHandler.get_recent_source_ids(self.current_user):
            self.push_all(action='skyportal/FETCH_RECENT_SOURCES')

        return self.success()
