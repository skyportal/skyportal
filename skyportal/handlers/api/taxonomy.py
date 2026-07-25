from typing import Any

import sqlalchemy as sa
import yaml
from jsonschema.exceptions import ValidationError as JSONValidationError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import selectinload
from tdtax import schema, validate

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env

from ...models import Classification, Group, Taxonomy
from ..base import BaseHandler

_, cfg = load_env()


class TaxonomyPostBody(BaseModel):
    """Request body for posting a new taxonomy."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Short string to make this taxonomy memorable to end users."
    )
    version: str = Field(description="Semantic version of this taxonomy name")
    hierarchy: dict[str, Any] | None = Field(
        default=None,
        description="Nested JSON describing the taxonomy which should be "
        "validated against a schema before entry. One of `hierarchy` or "
        "`hierarchy_file` must be provided.",
    )
    hierarchy_file: str | None = Field(
        default=None,
        description="YAML string describing the taxonomy, parsed into "
        "`hierarchy` when provided.",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should "
        "be able to view the taxonomy. Defaults to the public group.",
    )
    provenance: str | None = Field(
        default=None,
        description="Identifier (e.g., URL or git hash) that uniquely ties "
        "this taxonomy back to an origin or place of record",
    )
    isLatest: bool = Field(
        default=True,
        description="Consider this version of the taxonomy with this name "
        "the latest? Defaults to True.",
    )


class TaxonomyPostResponse(BaseModel):
    """Data payload returned when posting a taxonomy."""

    taxonomy_id: int = Field(description="New taxonomy ID")


class TaxonomyPutBody(BaseModel):
    """Request body for updating a taxonomy."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        description="Short string to make this taxonomy memorable to end users.",
    )
    version: str | None = Field(
        default=None, description="Semantic version of this taxonomy name"
    )
    provenance: str | None = Field(
        default=None,
        description="Identifier (e.g., URL or git hash) that uniquely ties "
        "this taxonomy back to an origin or place of record",
    )
    isLatest: bool | None = Field(
        default=None,
        description="Consider this version of the taxonomy with this name the latest?",
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should "
        "be able to view the taxonomy.",
    )
    hierarchy: dict[str, Any] | None = Field(
        default=None,
        description="Not editable; upload a new taxonomy if a hierarchy "
        "change is desired.",
    )


class TaxonomyHandler(BaseHandler):
    @auth_or_token
    async def get(self, taxonomy_id: int | None = None):
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

        async with self.AsyncSession() as session:
            if taxonomy_id is not None:
                try:
                    taxonomy_id = int(taxonomy_id)
                except (TypeError, ValueError):
                    return self.error(f"Invalid taxonomy_id: {taxonomy_id}")
                taxonomy = await Taxonomy.get_taxonomy_usable_by_user(
                    taxonomy_id,
                    self.current_user,
                    session,
                )
                if taxonomy is None or len(taxonomy) == 0:
                    return self.error(
                        "Taxonomy does not exist or is not available to user."
                    )

                return self.success(data=taxonomy[0])

            query_result = await session.scalars(
                Taxonomy.select(session.user_or_token)
                .options(selectinload(Taxonomy.groups))
                .where(
                    Taxonomy.groups.any(
                        Group.id.in_(
                            [g.id for g in self.current_user.accessible_groups]
                        )
                    )
                )
            )
            taxonomies = query_result.unique().all()
            taxonomies = [
                {
                    **taxonomy.to_dict(),
                    "groups": [group.to_dict() for group in taxonomy.groups],
                }
                for taxonomy in taxonomies
            ]
            return self.success(data=taxonomies)

    @permissions(["Post taxonomy"])
    async def post(self, *, body: TaxonomyPostBody = None) -> TaxonomyPostResponse:
        """
        ---
        summary: Post new taxonomy
        description: Post new taxonomy
        tags:
          - taxonomies
        """
        body = self.parse_body(TaxonomyPostBody)
        name = body.name
        version = body.version

        hierarchy = body.hierarchy
        if body.hierarchy_file is not None:
            hierarchy_json = yaml.safe_load(body.hierarchy_file)
            if isinstance(hierarchy_json, list):
                hierarchy_json = hierarchy_json[0]
            hierarchy = hierarchy_json

        async with self.AsyncSession() as session:
            existing_result = await session.scalars(
                Taxonomy.select(session.user_or_token)
                .where(Taxonomy.name == name)
                .where(Taxonomy.version == version)
            )
            existing_matches = existing_result.all()
            if len(existing_matches) != 0:
                return self.error(
                    "That version/name combination is already "
                    "present. If you really want to replace this "
                    "then delete the appropriate entry."
                )

            # Ensure a valid taxonomy
            if hierarchy is None:
                return self.error("A JSON of the taxonomy must be given")

            try:
                validate(hierarchy, schema)
            except JSONValidationError:
                return self.error("Hierarchy does not validate against the schema.")

            # establish the groups to use
            user_accessible_group_ids = [
                g.id for g in self.current_user.accessible_groups
            ]

            group_ids = body.group_ids
            if not group_ids:
                public_group = await session.scalar(
                    sa.select(Group.id).where(
                        Group.name == cfg["misc.public_group_name"]
                    )
                )
                if public_group is None:
                    return self.error(
                        f'No group_ids were specified and the public group "{cfg["misc.public_group_name"]}" does not exist. Cannot post taxonomy.'
                    )
                group_ids = [public_group]

            group_ids = [gid for gid in group_ids if gid in user_accessible_group_ids]
            if not group_ids:
                return self.error(
                    f"Invalid group IDs field ({group_ids}): "
                    "You must provide one or more valid group IDs."
                )
            groups_result = await session.scalars(
                Group.select(session.user_or_token).where(Group.id.in_(group_ids))
            )
            groups = groups_result.all()

            provenance = body.provenance

            # update others with this name
            # TODO: deal with the same name but different groups?
            isLatest = body.isLatest
            if isLatest:
                to_update_result = await session.scalars(
                    Taxonomy.select(session.user_or_token).where(
                        Taxonomy.name == name, Taxonomy.isLatest.is_(True)
                    )
                )
                taxonomies_to_update = to_update_result.all()
                if len(taxonomies_to_update) > 0:
                    for tax in taxonomies_to_update:
                        tax.isLatest = False
                        session.add(tax)

            taxonomy = Taxonomy(
                name=name,
                hierarchy=hierarchy,
                provenance=provenance,
                version=version,
                isLatest=isLatest,
                groups=groups,
            )

            session.add(taxonomy)
            await session.commit()

            self.push_all(action="skyportal/REFRESH_TAXONOMIES")
            return self.success(data={"taxonomy_id": taxonomy.id})

    @permissions(["Post taxonomy"])
    async def put(self, taxonomy_id: int, *, body: TaxonomyPutBody = None):
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
        body = self.parse_body(TaxonomyPutBody)

        if body.hierarchy is not None:
            return self.error(
                "Editing the hierarchy not allowed, upload a new taxonomy if this change is desired."
            )

        async with self.AsyncSession() as session:
            # permission check
            stmt = Taxonomy.select(session.user_or_token, mode="update").where(
                Taxonomy.id == int(taxonomy_id)
            )
            put_result = await session.scalars(stmt)
            taxonomy = put_result.first()
            if taxonomy is None:
                return self.error(f"Missing taxonomy with ID {taxonomy_id}")

            group_ids = body.group_ids
            if group_ids:
                user_accessible_group_ids = [
                    g.id for g in self.current_user.accessible_groups
                ]
                group_ids = [
                    gid for gid in group_ids if gid in user_accessible_group_ids
                ]
                groups_result = await session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                )
                groups = groups_result.all()
                taxonomy.groups = groups

            for field in ("name", "version", "provenance", "isLatest"):
                if field in body.model_fields_set:
                    setattr(taxonomy, field, getattr(body, field))

            await session.commit()

            self.push_all(action="skyportal/REFRESH_TAXONOMIES")
            return self.success()

    @permissions(["Delete taxonomy"])
    async def delete(self, taxonomy_id: int):
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

        async with self.AsyncSession() as session:
            cls_result = await session.scalars(
                sa.select(Classification).where(
                    Classification.taxonomy_id == taxonomy_id
                )
            )
            classification = cls_result.first()
            if classification is not None:
                return self.error(
                    f"Cannot delete taxonomy {taxonomy_id} because it has associated classifications."
                )

            del_result = await session.scalars(
                Taxonomy.select(session.user_or_token, mode="delete").where(
                    Taxonomy.id == taxonomy_id
                )
            )
            taxonomy = del_result.first()
            if taxonomy is None:
                return self.error(
                    f"Taxonomy {taxonomy_id} does not exist or is not available to user."
                )

            await session.delete(taxonomy)
            await session.commit()

            self.push_all(action="skyportal/REFRESH_TAXONOMIES")
            return self.success()
