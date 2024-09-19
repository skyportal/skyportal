from tdtax import schema, validate
from jsonschema.exceptions import ValidationError as JSONValidationError
import yaml

from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import Taxonomy, Group


class TaxonomyHandler(BaseHandler):
    @auth_or_token
    def get(self, taxonomy_id=None):
        """
        ---
        single:
          summary: Get a taxonomy
          description: Retrieve a taxonomy
          tags:
            - taxonomies
          parameters:
            - in: path
              name: taxonomy_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleTaxonomy
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Get all taxonomies
          description: Get all the taxonomies
          tags:
            - taxonomies
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfTaxonomys
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:
            if taxonomy_id is not None:
                taxonomy = Taxonomy.get_taxonomy_usable_by_user(
                    taxonomy_id,
                    self.current_user,
                    session,
                )
                if taxonomy is None or len(taxonomy) == 0:
                    return self.error(
                        'Taxonomy does not exist or is not available to user.'
                    )

                return self.success(data=taxonomy[0])

            query = session.scalars(
                Taxonomy.select(session.user_or_token).where(
                    Taxonomy.groups.any(
                        Group.id.in_(
                            [g.id for g in self.current_user.accessible_groups]
                        )
                    )
                )
            )
            taxonomies = query.unique().all()
            taxonomies = [
                {
                    **taxonomy.to_dict(),
                    'groups': [group.to_dict() for group in taxonomy.groups],
                }
                for taxonomy in taxonomies
            ]
            return self.success(data=taxonomies)

    @permissions(['Post taxonomy'])
    def post(self):
        """
        ---
        summary: Post new taxonomy
        description: Post new taxonomy
        tags:
          - taxonomies
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                    description: |
                      Short string to make this taxonomy memorable
                      to end users.
                  hierarchy:
                    type: object
                    description: |
                       Nested JSON describing the taxonomy
                       which should be validated against
                       a schema before entry
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups should be
                      able to view comment. Defaults to all of requesting
                      user's groups.
                  version:
                    type: string
                    description: |
                      Semantic version of this taxonomy name
                  provenance:
                    type: string
                    description: |
                      Identifier (e.g., URL or git hash) that
                      uniquely ties this taxonomy back
                      to an origin or place of record
                  isLatest:
                    type: boolean
                    description: |
                      Consider this version of the taxonomy with this
                      name the latest? Defaults to True.
                required:
                  - name
                  - hierarchy
                  - version

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
                            taxonomy_id:
                              type: integer
                              description: New taxonomy ID
        """
        data = self.get_json()
        name = data.get('name', None)
        if name is None:
            return self.error("A name must be provided for a taxonomy")

        version = data.get('version', None)
        if version is None:
            return self.error("A version string must be provided for a taxonomy")

        hierarchy_file = data.get('hierarchy_file', None)
        if hierarchy_file is not None:
            data['hierarchy'] = yaml.safe_load(hierarchy_file)[0]
            del data['hierarchy_file']

        with self.Session() as session:
            existing_matches = session.scalars(
                Taxonomy.select(session.user_or_token)
                .where(Taxonomy.name == name)
                .where(Taxonomy.version == version)
            ).all()
            if len(existing_matches) != 0:
                return self.error(
                    "That version/name combination is already "
                    "present. If you really want to replace this "
                    "then delete the appropriate entry."
                )

            # Ensure a valid taxonomy
            hierarchy = data.get('hierarchy', None)
            if hierarchy is None:
                return self.error("A JSON of the taxonomy must be given")

            try:
                validate(hierarchy, schema)
            except JSONValidationError:
                return self.error("Hierarchy does not validate against the schema.")

            # establish the groups to use
            user_group_ids = [g.id for g in self.current_user.groups]
            user_accessible_group_ids = [
                g.id for g in self.current_user.accessible_groups
            ]

            group_ids = data.pop("group_ids", user_group_ids)
            if group_ids == []:
                group_ids = user_group_ids
            group_ids = [gid for gid in group_ids if gid in user_accessible_group_ids]
            if not group_ids:
                return self.error(
                    f"Invalid group IDs field ({group_ids}): "
                    "You must provide one or more valid group IDs."
                )
            groups = session.scalars(
                Group.select(session.user_or_token).where(Group.id.in_(group_ids))
            ).all()

            provenance = data.get('provenance', None)

            # update others with this name
            # TODO: deal with the same name but different groups?
            isLatest = data.get('isLatest', True)
            if isLatest:
                taxonomy_update = session.scalars(
                    Taxonomy.select(session.user_or_token).where(Taxonomy.name == name)
                ).first()
                if taxonomy_update is not None:
                    taxonomy_update.isLatest = False
                    session.add(taxonomy_update)

            taxonomy = Taxonomy(
                name=name,
                hierarchy=hierarchy,
                provenance=provenance,
                version=version,
                isLatest=isLatest,
                groups=groups,
            )

            session.add(taxonomy)
            session.commit()

            self.push_all(action="skyportal/REFRESH_TAXONOMIES")

            return self.success(data={'taxonomy_id': taxonomy.id})

    @permissions(['Post taxonomy'])
    def put(self, taxonomy_id):
        """
        ---
        summary: Update a taxonomy
        description: Update taxonomy
        tags:
          - taxonomies
        parameters:
          - in: path
            name: taxonomy_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: TaxonomyNoID
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
        data['id'] = int(taxonomy_id)

        hierarchy = data.get('hierarchy', None)
        if hierarchy is not None:
            return self.error(
                "Editing the hierarchy not allowed, upload a new taxonomy if this change is desired."
            )

        with self.Session() as session:
            # permission check
            stmt = Taxonomy.select(session.user_or_token, mode="update").where(
                Taxonomy.id == int(taxonomy_id)
            )
            taxonomy = session.scalars(stmt).first()
            if taxonomy is None:
                return self.error(f'Missing taxonomy with ID {taxonomy_id}')

            group_ids = data.pop("group_ids", None)
            if group_ids:
                user_accessible_group_ids = [
                    g.id for g in self.current_user.accessible_groups
                ]
                group_ids = [
                    gid for gid in group_ids if gid in user_accessible_group_ids
                ]
                groups = session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                ).all()
                taxonomy.groups = groups

            for k in data:
                setattr(taxonomy, k, data[k])

            session.commit()

            self.push_all(action="skyportal/REFRESH_TAXONOMIES")
            return self.success()

    @permissions(['Delete taxonomy'])
    def delete(self, taxonomy_id):
        """
        ---
        summary: Delete a taxonomy
        description: Delete a taxonomy
        tags:
          - taxonomies
        parameters:
          - in: path
            name: taxonomy_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            taxonomy = session.scalars(
                Taxonomy.select(session.user_or_token, mode='delete').where(
                    Taxonomy.id == taxonomy_id
                )
            ).first()
            if taxonomy is None:
                return self.error(
                    'Taxonomy does not exist or is not available to user.'
                )

            session.delete(taxonomy)
            session.commit()

            self.push_all(action="skyportal/REFRESH_TAXONOMIES")

            return self.success()
