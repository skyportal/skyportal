import arrow
import sqlalchemy as sa
from sqlalchemy import func
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from baselayer.app.flow import Flow

from ..base import BaseHandler
from ...models import (
    Group,
    Classification,
    ClassificationVote,
    SourceLabel,
    Taxonomy,
    Obj,
    User,
)

_, cfg = load_env()

DEFAULT_CLASSIFICATIONS_PER_PAGE = 100
MAX_CLASSIFICATIONS_PER_PAGE = 500


def post_classification(data, user_id, session):
    """Post classification to database.
    data: dict
        Source dictionary
    user_id : int
        SkyPortal ID of User posting the GcnEvent
    session: sqlalchemy.Session
        Database session for this transaction
    """

    user = session.scalar(sa.select(User).where(User.id == user_id))
    obj_id = data['obj_id']

    group_ids = data.pop("group_ids", [])
    if not isinstance(group_ids, list) or len(group_ids) == 0:
        public_group = session.scalar(
            sa.select(Group.id).where(Group.name == cfg['misc.public_group_name'])
        )
        if public_group is None:
            raise ValueError(
                f'No group_ids were specified and the public group "{cfg["misc.public_group_name"]}" does not exist. Cannot post classification'
            )
        group_ids = [public_group]

    origin = data.get('origin')

    ml = data.get('ml', False)
    if ml in [True, "True", "t", "true"]:
        ml = True
    elif ml in [False, "False", "f", "false"]:
        ml = False
    else:
        raise ValueError(
            f"If provided, ml must be one of True, False, 'True', 'False', 't', 'f', 'true', 'false' (got {ml})"
        )

    # check the taxonomy
    taxonomy_id = data["taxonomy_id"]
    taxonomy = session.scalars(
        Taxonomy.select(session.user_or_token).where(Taxonomy.id == taxonomy_id)
    ).first()
    if taxonomy is None:
        raise ValueError(f'Cannot find a taxonomy with ID: {taxonomy_id}.')

    def allowed_classes(hierarchy):
        if "class" in hierarchy:
            yield hierarchy["class"]

        if "subclasses" in hierarchy:
            for item in hierarchy.get("subclasses", []):
                yield from allowed_classes(item)

    if data['classification'] not in allowed_classes(taxonomy.hierarchy):
        raise ValueError(
            f"That classification ({data['classification']}) "
            'is not in the allowed classes for the chosen '
            f'taxonomy (id={taxonomy_id}'
        )

    probability = data.get('probability')
    if probability is not None:
        if probability < 0 or probability > 1:
            raise ValueError(
                f"That probability ({probability}) is outside "
                "the allowable range (0-1)."
            )

    groups = session.scalars(Group.select(user).where(Group.id.in_(group_ids))).all()
    if {g.id for g in groups} != set(group_ids):
        raise ValueError(f'Cannot find one or more groups with IDs: {group_ids}.')

    classification = Classification(
        classification=data['classification'],
        obj_id=obj_id,
        origin=origin,
        probability=probability,
        ml=ml,
        taxonomy_id=data["taxonomy_id"],
        author=user,
        author_name=user.username,
        groups=groups,
    )
    session.add(classification)

    # voting
    add_vote = True
    if 'vote' in data:
        if data['vote'] is False:
            add_vote = False

    if add_vote:
        new_vote = ClassificationVote(
            classification=classification, voter_id=user.id, vote=1
        )
        session.add(new_vote)

    # labelling
    add_label = True
    if 'label' in data:
        if data['label'] is False:
            add_label = False

    if add_label:
        for group_id in group_ids:
            source_label = session.scalars(
                SourceLabel.select(session.user_or_token)
                .where(SourceLabel.obj_id == obj_id)
                .where(SourceLabel.group_id == group_id)
                .where(SourceLabel.labeller_id == user_id)
            ).first()
            if source_label is None:
                label = SourceLabel(
                    obj_id=obj_id,
                    labeller_id=user_id,
                    group_id=group_id,
                )
                session.add(label)

    session.commit()

    flow = Flow()
    flow.push(
        '*',
        'skyportal/REFRESH_SOURCE',
        payload={'obj_key': classification.obj.internal_key},
    )
    # flow.push(
    #    '*',
    #    'skyportal/REFRESH_CANDIDATE',
    #    payload={'id': classification.obj.internal_key},
    # )

    return classification.id


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
            - in: query
              name: includeTaxonomy
              nullable: true
              schema:
                type: boolean
              description: |
                Return associated taxonomy.
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
            name: includeTaxonomy
            nullable: true
            schema:
              type: boolean
            description: |
              Return associated taxonomy.
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

        try:
            page_number = int(self.get_query_argument('pageNumber', 1))
            n_per_page = min(
                int(
                    self.get_query_argument(
                        "numPerPage", DEFAULT_CLASSIFICATIONS_PER_PAGE
                    )
                ),
                MAX_CLASSIFICATIONS_PER_PAGE,
            )
        except ValueError:
            return self.error(
                f'Cannot parse inputs pageNumber ({page_number}) '
                f'or numPerPage ({n_per_page}) as an integers.'
            )

        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        include_taxonomy = self.get_query_argument('includeTaxonomy', False)

        with self.Session() as session:
            if classification_id is not None:
                classification = session.scalars(
                    Classification.select(session.user_or_token).where(
                        Classification.id == classification_id
                    )
                ).first()
                if classification is None:
                    return self.error(
                        f'Cannot find classification with ID: {classification_id}.'
                    )
                data_out = classification.to_dict()
                if include_taxonomy:
                    data_out['taxonomy'] = classification.taxonomy.to_dict()
                return self.success(data=data_out)

            # get owned
            classifications = Classification.select(session.user_or_token)

            if start_date:
                start_date = str(arrow.get(start_date.strip()).datetime)
                classifications = classifications.where(
                    Classification.created_at >= start_date
                )
            if end_date:
                end_date = str(arrow.get(end_date.strip()).datetime)
                classifications = classifications.where(
                    Classification.created_at <= end_date
                )

            count_stmt = sa.select(func.count()).select_from(classifications)
            total_matches = session.execute(count_stmt).scalar()
            classifications = classifications.limit(n_per_page).offset(
                (page_number - 1) * n_per_page
            )
            classifications = session.scalars(classifications).unique().all()

            data_out = []
            for classification in classifications:
                req = classification.to_dict()
                if include_taxonomy:
                    req['taxonomy'] = req.taxonomy.to_dict()
                data_out.append(req)

            info = {}
            info["classifications"] = data_out
            info["totalMatches"] = int(total_matches)
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
                  origin:
                    type: string
                    description: |
                      String describing the source of this classification.
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
                      able to view classification. Defaults to the public group.
                  vote:
                    type: boolean
                    nullable: true
                    description: |
                      Add vote associated with classification.
                  label:
                    type: boolean
                    nullable: true
                    description: |
                      Add label associated with classification.
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

        with self.Session() as session:
            if 'classifications' in data:
                classification_ids = []
                for classification in data['classifications']:
                    try:
                        classification_id = post_classification(
                            classification, self.associated_user_object.id, session
                        )
                    except Exception as e:
                        return self.error(f'Error posting classification: {str(e)}')
                    classification_ids.append(classification_id)
                return self.success(data={'classification_ids': classification_ids})
            else:
                try:
                    classification_id = post_classification(
                        data, self.associated_user_object.id, session
                    )
                except Exception as e:
                    return self.error(f'Error posting classification: {str(e)}')
                return self.success(data={"classification_id": classification_id})

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

        with self.Session() as session:
            c = session.scalars(
                Classification.select(session.user_or_token, mode="update").where(
                    Classification.id == classification_id
                )
            ).first()
            if c is None:
                return self.error(
                    f'Cannot find a classification with ID: {classification_id}.'
                )

            data = self.get_json()
            group_ids = data.pop("group_ids", None)
            data['id'] = classification_id

            ml = data.get('ml', False)
            if ml in [True, "True", "t", "true"]:
                ml = True
            elif ml in [False, "False", "f", "false"]:
                ml = False
            else:
                raise ValueError(
                    f"If provided, ml must be one of True, False, 'True', 'False', 't', 'f', 'true', 'false' (got {ml})"
                )
            data['ml'] = ml

            schema = Classification.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )

            for k in data:
                setattr(c, k, data[k])

            if group_ids is not None:
                groups = session.scalars(
                    Group.select(self.current_user).where(Group.id.in_(group_ids))
                ).all()
                if {g.id for g in groups} != set(group_ids):
                    return self.error(
                        f'Cannot find one or more groups with IDs: {group_ids}.'
                    )

                c.groups = groups

            session.commit()
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
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  label:
                    type: boolean
                    nullable: true
                    description: |
                      Add label associated with classification.
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            c = session.scalars(
                Classification.select(session.user_or_token, mode="delete").where(
                    Classification.id == classification_id
                )
            ).first()
            if c is None:
                return self.error(
                    f'Cannot find a classification with ID: {classification_id}.'
                )

            data = self.get_json()
            add_label = data.get('label', True)

            obj_key = c.obj.internal_key
            obj_id = c.obj.id
            group_ids = [group.id for group in c.groups]
            session.delete(c)

            if add_label:
                for group_id in group_ids:
                    source_label = session.scalars(
                        SourceLabel.select(session.user_or_token)
                        .where(SourceLabel.obj_id == obj_id)
                        .where(SourceLabel.group_id == group_id)
                        .where(
                            SourceLabel.labeller_id == self.associated_user_object.id
                        )
                    ).first()
                    if source_label is None:
                        label = SourceLabel(
                            obj_id=obj_id,
                            labeller_id=self.associated_user_object.id,
                            group_id=group_id,
                        )
                        session.add(label)

            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': obj_key},
            )
            self.push_all(
                action='skyportal/REFRESH_CANDIDATE',
                payload={'id': obj_key},
            )

            session.commit()

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

        with self.Session() as session:
            classifications = (
                session.scalars(
                    Classification.select(session.user_or_token).where(
                        Classification.obj_id == obj_id
                    )
                )
                .unique()
                .all()
            )

            classifications_json = []
            for classification in classifications:
                classification_dict = classification.to_dict()
                classification_dict['votes'] = [
                    v.to_dict() for v in classification.votes
                ]
                classifications_json.append(classification_dict)

            return self.success(data=classifications_json)

    @auth_or_token
    def delete(self, obj_id):
        """
        ---
        description: Delete all of an object's classifications
        tags:
          - classifications
          - sources
        parameters:
          - in: path
            name: classification_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  label:
                    type: boolean
                    nullable: true
                    description: |
                      Add label associated with classification.
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            classifications = (
                session.scalars(
                    Classification.select(session.user_or_token, mode="delete").where(
                        Classification.obj_id == obj_id
                    )
                )
                .unique()
                .all()
            )

            data = self.get_json()
            add_label = data.get('label', True)

            for c in classifications:
                obj_key = c.obj.internal_key
                obj_id = c.obj.id
                group_ids = [group.id for group in c.groups]
                session.delete(c)

                if add_label:
                    for group_id in group_ids:
                        source_label = session.scalars(
                            SourceLabel.select(session.user_or_token)
                            .where(SourceLabel.obj_id == obj_id)
                            .where(SourceLabel.group_id == group_id)
                            .where(
                                SourceLabel.labeller_id
                                == self.associated_user_object.id
                            )
                        ).first()
                        if source_label is None:
                            label = SourceLabel(
                                obj_id=obj_id,
                                labeller_id=self.associated_user_object.id,
                                group_id=group_id,
                            )
                            session.add(label)

            session.commit()

            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': obj_key},
            )
            self.push_all(
                action='skyportal/REFRESH_CANDIDATE',
                payload={'id': obj_key},
            )

            return self.success()


class ObjClassificationQueryHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: find the sources with classifications
        tags:
          - source
        parameters:
        - in: query
          name: startDate
          nullable: true
          schema:
            type: string
          description: |
            Arrow-parseable date string (e.g. 2020-01-01) for when the classification was made. If provided, filter by
            created_at >= startDate
        - in: query
          name: endDate
          nullable: true
          schema:
            type: string
          description: |
            Arrow-parseable date string (e.g. 2020-01-01) for when the classification was made. If provided, filter by
            created_at <= endDate
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
                            type: array
                            items:
                              type: integer
                            description: |
                              List of obj IDs with classifications
            400:
              content:
                application/json:
                  schema: Error
        """

        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)

        with self.Session() as session:
            # get owned
            classifications = Classification.select(session.user_or_token)

            if start_date:
                start_date = str(arrow.get(start_date.strip()).datetime)
                classifications = classifications.where(
                    Classification.created_at >= start_date
                )
            if end_date:
                end_date = str(arrow.get(end_date.strip()).datetime)
                classifications = classifications.where(
                    Classification.created_at <= end_date
                )

            classifications_subquery = classifications.subquery()

            stmt = sa.select(Obj.id).join(
                classifications_subquery, classifications_subquery.c.obj_id == Obj.id
            )
            obj_ids = session.scalars(stmt.distinct()).all()

            return self.success(data=obj_ids)


class ClassificationVotesHandler(BaseHandler):
    @auth_or_token
    def post(self, classification_id):
        """
        ---
        description: Vote for a classification.
        tags:
          - classifications
          - classification_votes
        parameters:
          - in: path
            name: classification_id
            required: true
            schema:
              type: string
            description: |
              ID of classification to indicate the vote for
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  vote:
                    type: integer
                    description: |
                      Upvote or downvote a classification
                required:
                  - vote
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        data = self.get_json()
        vote = data.get("vote")
        if vote is None:
            return self.error("Missing required parameter: `vote`")

        with self.Session() as session:
            classification = session.scalars(
                Classification.select(session.user_or_token).where(
                    Classification.id == classification_id
                )
            ).first()
            if classification is None:
                return self.error(
                    f"Cannot find classification with ID {classification_id}"
                )

            classification_vote = session.scalars(
                ClassificationVote.select(session.user_or_token).where(
                    ClassificationVote.classification_id == classification_id,
                    ClassificationVote.voter_id == self.associated_user_object.id,
                )
            ).first()
            if classification_vote is None:
                new_vote = ClassificationVote(
                    classification_id=classification_id,
                    voter_id=self.associated_user_object.id,
                    vote=vote,
                )
                session.add(new_vote)
            else:
                classification_vote.vote = vote

            obj_id = classification.obj.id
            group_ids = [group.id for group in classification.groups]
            for group_id in group_ids:
                source_label = session.scalars(
                    SourceLabel.select(session.user_or_token)
                    .where(SourceLabel.obj_id == obj_id)
                    .where(SourceLabel.group_id == group_id)
                    .where(SourceLabel.labeller_id == self.associated_user_object.id)
                ).first()
            if source_label is None:
                label = SourceLabel(
                    obj_id=obj_id,
                    labeller_id=self.associated_user_object.id,
                    group_id=group_id,
                )
                session.add(label)

            session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": classification.obj.internal_key},
            )
            return self.success()

    @auth_or_token
    def delete(self, classification_id):
        """
        ---
        description: Delete classification vote.
        tags:
          - classifications
          - classification_votes
        parameters:
          - in: path
            name: classification_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            classification = session.scalars(
                Classification.select(session.user_or_token).where(
                    Classification.id == classification_id
                )
            ).first()
            if classification is None:
                return self.error(
                    f"Cannot find classification with ID {classification_id}"
                )

            classification_vote = session.scalars(
                ClassificationVote.select(session.user_or_token, mode="delete").where(
                    ClassificationVote.classification_id == classification_id,
                    ClassificationVote.voter_id == self.associated_user_object.id,
                )
            ).first()
            session.delete(classification_vote)

            obj_id = classification.obj.id
            group_ids = [group.id for group in classification.groups]
            for group_id in group_ids:
                source_label = session.scalars(
                    SourceLabel.select(session.user_or_token)
                    .where(SourceLabel.obj_id == obj_id)
                    .where(SourceLabel.group_id == group_id)
                    .where(SourceLabel.labeller_id == self.associated_user_object.id)
                ).first()
            if source_label is None:
                label = SourceLabel(
                    obj_id=obj_id,
                    labeller_id=self.associated_user_object.id,
                    group_id=group_id,
                )
                session.add(label)

            session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": classification.obj.internal_key},
            )

            return self.success()
