import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import selectinload

from baselayer.app.access import permissions
from baselayer.log import make_log

from ...models import Group, Spectrum
from ...utils.naive_datetime import utcnow_naive
from ..base import BaseHandler

log = make_log("api/data_sharing")

# Supported data types -> (association table, data-id column, data table).
# Whitelist only; these values are interpolated into SQL, so they must never
# come from the client.
DATA_TYPES = {
    "spectra": ("group_spectra", "spectr_id", "spectra"),
    "photometry": ("group_photometry", "photometr_id", "photometry"),
}


class BulkDataShareBody(BaseModel):
    """Add or remove a target group across data selected by a source group or a
    set of objects. Provide exactly one of `from_group_id` or `obj_ids`."""

    model_config = ConfigDict(extra="forbid")

    from_group_id: int | None = Field(
        default=None,
        description="Group whose existing data-shares define the set to act on. "
        "Mutually exclusive with obj_ids.",
    )
    obj_ids: list[str] | None = Field(
        default=None,
        description="Objects whose data (in any group) to act on. Mutually "
        "exclusive with from_group_id.",
    )
    to_group_id: int = Field(
        description="Group to grant (or revoke) access for on that data."
    )
    data_types: list[str] = Field(
        default_factory=lambda: ["spectra", "photometry"],
        description='Data to act on: any of "spectra", "photometry".',
    )
    action: str = Field(
        default="add", description='"add" to share, "remove" to unshare.'
    )


class BulkDataShareHandler(BaseHandler):
    @permissions(["System admin"])
    async def post(self):
        """
        ---
        summary: Bulk-share spectra/photometry with a group
        description: |
            Grant (or revoke) a target group's access to every spectrum and/or
            photometry point selected either by a source group (`from_group_id`)
            or by a set of objects (`obj_ids`), in one set-based operation.
            Additive and idempotent: it only inserts or deletes group
            associations and never touches the data itself. The supported way to
            re-expose narrowly-shared legacy/imported data collaboration-wide.
        tags:
          - groups
        requestBody:
          content:
            application/json:
              schema:
                type: object
                required:
                  - to_group_id
                properties:
                  from_group_id:
                    type: integer
                    description: Source group; mutually exclusive with obj_ids.
                  obj_ids:
                    type: array
                    items:
                      type: string
                    description: Source objects; mutually exclusive with from_group_id.
                  to_group_id:
                    type: integer
                  data_types:
                    type: array
                    items:
                      type: string
                      enum: [spectra, photometry]
                  action:
                    type: string
                    enum: [add, remove]
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
        body = self.parse_body(BulkDataShareBody)
        if body.action not in ("add", "remove"):
            return self.error('`action` must be "add" or "remove".')
        if not body.data_types:
            return self.error("`data_types` must not be empty.")
        unknown = set(body.data_types) - set(DATA_TYPES)
        if unknown:
            return self.error(
                f"Unknown data_types {sorted(unknown)}; allowed: {sorted(DATA_TYPES)}."
            )
        scope_by_objs = bool(body.obj_ids)
        if scope_by_objs == (body.from_group_id is not None):
            return self.error("Provide exactly one of `from_group_id` or `obj_ids`.")
        if not scope_by_objs and body.from_group_id == body.to_group_id:
            return self.error("`from_group_id` and `to_group_id` must differ.")

        async with self.AsyncSession() as session:
            group_ids = [body.to_group_id]
            if not scope_by_objs:
                group_ids.append(body.from_group_id)
            for gid in group_ids:
                group = await session.scalar(
                    Group.select(session.user_or_token).where(Group.id == gid)
                )
                if group is None:
                    return self.error(f"Cannot find or access group {gid}.")

            counts = {}
            for data_type in body.data_types:
                assoc, col, data_table = DATA_TYPES[data_type]
                if scope_by_objs and body.action == "add":
                    # Share every point/spectrum of the given objects, whatever
                    # group it currently sits in. NOT EXISTS keeps it idempotent.
                    stmt = sa.text(
                        f"INSERT INTO {assoc} (group_id, {col}, created_at, modified) "  # noqa: S608
                        f"SELECT :to, d.id, :now, :now FROM {data_table} d "
                        f"WHERE d.obj_id = ANY(:obj_ids) AND NOT EXISTS "
                        f"(SELECT 1 FROM {assoc} x WHERE x.{col} = d.id "
                        f"AND x.group_id = :to)"
                    )
                    params = {
                        "to": body.to_group_id,
                        "obj_ids": body.obj_ids,
                        "now": utcnow_naive(),
                    }
                elif scope_by_objs:
                    stmt = sa.text(
                        f"DELETE FROM {assoc} x USING {data_table} d "  # noqa: S608
                        f"WHERE x.{col} = d.id AND x.group_id = :to "
                        f"AND d.obj_id = ANY(:obj_ids)"
                    )
                    params = {"to": body.to_group_id, "obj_ids": body.obj_ids}
                elif body.action == "add":
                    # NOT EXISTS keeps it idempotent regardless of the table's
                    # PK shape (group_spectra has a surrogate id; group_photometry
                    # a composite key), so a re-run adds nothing.
                    stmt = sa.text(
                        f"INSERT INTO {assoc} (group_id, {col}, created_at, modified) "  # noqa: S608
                        f"SELECT :to, src.{col}, :now, :now FROM {assoc} src "
                        f"WHERE src.group_id = :from_ AND NOT EXISTS "
                        f"(SELECT 1 FROM {assoc} x WHERE x.{col} = src.{col} "
                        f"AND x.group_id = :to)"
                    )
                    params = {
                        "to": body.to_group_id,
                        "from_": body.from_group_id,
                        "now": utcnow_naive(),
                    }
                else:
                    stmt = sa.text(
                        f"DELETE FROM {assoc} WHERE group_id = :to AND {col} IN "  # noqa: S608
                        f"(SELECT {col} FROM {assoc} WHERE group_id = :from_)"
                    )
                    params = {"to": body.to_group_id, "from_": body.from_group_id}
                result = await session.execute(stmt, params)
                counts[data_type] = result.rowcount
            await session.commit()

        source = (
            f"objs={len(body.obj_ids)}"
            if scope_by_objs
            else f"group {body.from_group_id}"
        )
        log(f"bulk data {body.action}: {source} -> {body.to_group_id}: {counts}")
        return self.success(data={"action": body.action, "counts": counts})


class SpectrumGroupsHandler(BaseHandler):
    @permissions(["System admin"])
    async def delete(self, spectrum_id, group_id):
        """
        ---
        summary: Remove a group from a spectrum
        description: |
            Revoke a single group's access to one spectrum. Used to undo an
            accidental over-share; refuses to remove a spectrum's only group.
        tags:
          - spectra
        parameters:
          - in: path
            name: spectrum_id
            required: true
            schema:
              type: integer
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
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            spectrum_id = int(spectrum_id)
            group_id = int(group_id)
        except (TypeError, ValueError):
            return self.error("spectrum_id and group_id must be integers.")

        async with self.AsyncSession() as session:
            spectrum = await session.scalar(
                Spectrum.select(session.user_or_token, mode="update")
                .options(selectinload(Spectrum.groups))
                .where(Spectrum.id == spectrum_id)
            )
            if spectrum is None:
                return self.error(
                    f"Cannot find spectrum {spectrum_id}, or you lack permission "
                    f"to modify it."
                )
            group_ids = {g.id for g in spectrum.groups}
            if group_id not in group_ids:
                return self.success(
                    data={"message": f"Group {group_id} is not on this spectrum."}
                )
            if len(group_ids) <= 1:
                return self.error("Refusing to remove a spectrum's only group.")
            spectrum.groups = [g for g in spectrum.groups if g.id != group_id]
            await session.commit()

        return self.success()
