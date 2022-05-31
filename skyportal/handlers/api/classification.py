import arrow
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Group, Classification, Taxonomy
from skyportal.handlers.api.user import notify_users

DEFAULT_CLASSIFICATIONS_PER_PAGE = 100
MAX_CLASSIFICATIONS_PER_PAGE = 500


class ClassificationHandler(BaseHandler):
    @auth_or_token
    def get(self, classification_id=None):
        """
        ---
        single:
          description: Retrieve a classification
          tags:
            - classifications
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
        multiple:
          description: Retrieve all classifications
          tags:
            - classifications
          parameters:
          - in: query
            name: startDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              created_at >= startDate
          - in: query
            name: endDate
            nullable: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              created_at <= endDate
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of sources to return per paginated request. Defaults to 100. Max 500.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for paginated query results. Defaults to 1
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
                              sources:
                                type: array
                                items:
                                  $ref: '#/components/schemas/Classification'
                              totalMatches:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error

        """

        page_number = self.get_query_argument('pageNumber', 1)
        n_per_page = min(
            int(
                self.get_query_argument("numPerPage", DEFAULT_CLASSIFICATIONS_PER_PAGE)
            ),
            MAX_CLASSIFICATIONS_PER_PAGE,
        )
        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)

        if classification_id is not None:
            classification = Classification.get_if_accessible_by(
                classification_id, self.current_user, raise_if_none=True
            )
            return self.success(data=classification)

        # get owned
        classifications = Classification.query_records_accessible_by(self.current_user)

        if start_date:
            start_date = str(arrow.get(start_date.strip()).datetime)
            classifications = classifications.filter(
                Classification.created_at >= start_date
            )
        if end_date:
            end_date = str(arrow.get(end_date.strip()).datetime)
            classifications = classifications.filter(
                Classification.created_at <= end_date
            )

        total_matches = classifications.count()
        classifications = classifications.limit(n_per_page).offset(
            (page_number - 1) * n_per_page
        )
        classifications = classifications.all()

        info = {}
        info["classifications"] = [req.to_dict() for req in classifications]
        info["totalMatches"] = int(total_matches)
        self.verify_and_commit()
        return self.success(data=info)

    @permissions(['Classify'])
    def post(self):
        """
        ---
        description: Post a classification
        tags:
          - classifications
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

        user_group_ids = [g.id for g in self.current_user.groups]
        group_ids = data.pop("group_ids", user_group_ids)
        groups = Group.get_if_accessible_by(
            group_ids, self.current_user, raise_if_none=True
        )

        author = self.associated_user_object

        # check the taxonomy
        taxonomy_id = data["taxonomy_id"]
        taxonomy = Taxonomy.get_if_accessible_by(
            taxonomy_id, self.current_user, raise_if_none=True
        )

        def allowed_classes(hierarchy):
            if "class" in hierarchy:
                yield hierarchy["class"]

            if "subclasses" in hierarchy:
                for item in hierarchy.get("subclasses", []):
                    yield from allowed_classes(item)

        if data['classification'] not in allowed_classes(taxonomy.hierarchy):
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
        print(data['classification'])
        notify_users(obj_id, "source", f"/source/{obj_id}", str(data['classification']))

        self.verify_and_commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': classification.obj.internal_key},
        )

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
        tags:
          - classifications
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
        c = Classification.get_if_accessible_by(
            classification_id, self.current_user, mode="update", raise_if_none=True
        )

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

        if group_ids is not None:
            groups = Group.get_if_accessible_by(
                group_ids, self.current_user, raise_if_none=True
            )
            c.groups = groups
        notify_users(
            c.obj.internal_key,
            "source",
            f"/source/{c.obj.internal_key}",
            data['classification'],
        )
        self.verify_and_commit()
        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': c.obj.internal_key},
        )
        self.push_all(
            action='skyportal/REFRESH_CANDIDATE',
            payload={'id': c.obj.internal_key},
        )
        return self.success()

    @permissions(['Classify'])
    def delete(self, classification_id):
        """
        ---
        description: Delete a classification
        tags:
          - classifications
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
        c = Classification.get_if_accessible_by(
            classification_id, self.current_user, mode="delete", raise_if_none=True
        )
        obj_key = c.obj.internal_key
        DBSession().delete(c)
        self.verify_and_commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': obj_key},
        )
        self.push_all(
            action='skyportal/REFRESH_CANDIDATE',
            payload={'id': obj_key},
        )

        return self.success()


class ObjClassificationHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        """
        ---
        description: Retrieve an object's classifications
        tags:
          - classifications
          - sources
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfClassifications
          400:
            content:
              application/json:
                schema: Error
        """

        classifications = (
            Classification.query_records_accessible_by(self.current_user)
            .filter(Classification.obj_id == obj_id)
            .all()
        )
        self.verify_and_commit()
        return self.success(data=classifications)
