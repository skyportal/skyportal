import sqlalchemy as sa
from skyportal_py_models.sharing import SharingPostBody
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from baselayer.app.access import permissions

from ...models import Group, GroupPhotometry, GroupUser, Photometry, Spectrum
from ..base import BaseHandler


class SharingHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(self, *, body: SharingPostBody = None):
        """
        ---
        summary: Share data with additional groups/users
        description: Share data with additional groups/users
        tags:
          - data sharing
          - photometry
          - spectra
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        body = self.parse_body(SharingPostBody)
        group_ids = body.groupIDs
        phot_ids = body.photometryIDs or []
        spec_ids = body.spectrumIDs or []
        if not phot_ids and not spec_ids:
            return self.error(
                "One of either `photometryIDs` or `spectrumIDs` must be provided."
            )

        async with self.AsyncSession() as session:
            valid_groups_result = await session.scalars(
                Group.select(session.user_or_token)
                .where(Group.id.in_(group_ids))
                .distinct()
            )
            valid_groups = valid_groups_result.all()
            valid_group_ids = [g.id for g in valid_groups]
            invalid_group_ids = [gid for gid in group_ids if gid not in valid_group_ids]

            if len(invalid_group_ids) > 0:
                return self.error(f"Invalid group IDs: {invalid_group_ids}.")
            groups = valid_groups

            phot_obj_ids = []
            spec_obj_internal_keys = []
            is_system_admin = "System admin" in self.associated_user_object.permissions

            if phot_ids:
                memberships = (
                    await session.execute(
                        sa.select(
                            GroupUser.group_id, GroupUser.can_share_photometry
                        ).where(GroupUser.user_id == self.associated_user_object.id)
                    )
                ).all()
                member_group_ids = {group_id for group_id, _ in memberships}
                # Groups in which this user may share photometry they don't own.
                shareable_group_ids = {
                    group_id for group_id, can_share in memberships if can_share
                }
                valid_phot_result = await session.scalars(
                    Photometry.select(session.user_or_token)
                    .options(selectinload(Photometry.groups))
                    .where(Photometry.id.in_(phot_ids))
                )
                # unique(): the access-control join fans out over the point's
                # groups/streams, so a point can come back more than once.
                valid_phot = valid_phot_result.unique().all()
                valid_phot_ids = [op.id for op in valid_phot]
                invalid_phot_ids = [
                    pid for pid in phot_ids if pid not in valid_phot_ids
                ]

                if len(invalid_phot_ids) > 0:
                    return self.error(f"Invalid photometry IDs: {invalid_phot_ids}.")

                # `can_share_photometry` only lets a user widen access within
                # their own collaborations, so re-sharing someone else's point
                # is limited to groups they belong to. Owners and system admins
                # keep the unrestricted behavior.
                if not is_system_admin and any(
                    phot.owner_id != self.associated_user_object.id
                    for phot in valid_phot
                ):
                    outside_group_ids = [
                        group.id for group in groups if group.id not in member_group_ids
                    ]
                    if outside_group_ids:
                        return self.error(
                            "Cannot share photometry you do not own with groups you "
                            f"are not a member of: {outside_group_ids}."
                        )

                for phot in valid_phot:
                    existing_group_ids = {g.id for g in phot.groups}
                    if (
                        phot.owner_id != self.associated_user_object.id
                        and not is_system_admin
                        and not existing_group_ids & shareable_group_ids
                    ):
                        return self.error(
                            f"Cannot share photometry id {phot.id}: you are not the owner and do not have sharing rights in any of its groups."
                        )
                    new_group_ids = [
                        group.id
                        for group in groups
                        if group.id not in existing_group_ids
                    ]
                    if new_group_ids:
                        # Insert the join rows directly. Appending to
                        # phot.groups marks the Photometry dirty, which trips
                        # its owner-only update check, and adding
                        # GroupPhotometry through the ORM trips the create
                        # check, which cannot handle a composite primary key.
                        # The checks above are the permission boundary here.
                        await session.execute(
                            pg_insert(GroupPhotometry.__table__)
                            .values(
                                [
                                    {"photometr_id": phot.id, "group_id": group_id}
                                    for group_id in new_group_ids
                                ]
                            )
                            .on_conflict_do_nothing()
                        )
                    phot_obj_ids.append(phot.obj_id)

            if spec_ids:
                valid_spec_result = await session.scalars(
                    Spectrum.select(session.user_or_token, mode="update")
                    .options(
                        selectinload(Spectrum.groups),
                        selectinload(Spectrum.obj),
                    )
                    .where(Spectrum.id.in_(spec_ids))
                )
                valid_spec = valid_spec_result.all()
                valid_spec_ids = [os.id for os in valid_spec]
                invalid_spec_ids = [
                    sid for sid in spec_ids if sid not in valid_spec_ids
                ]

                if len(invalid_spec_ids) > 0:
                    return self.error(
                        f"Cannot share spectrum IDs {invalid_spec_ids}: not found or you are not the owner."
                    )

                for spec in valid_spec:
                    existing_group_ids = {g.id for g in spec.groups}
                    for group in groups:
                        if group.id not in existing_group_ids:
                            spec.groups.append(group)
                    spec_obj_internal_keys.append(spec.obj.internal_key)

            await session.commit()

            phot_obj_ids = set(phot_obj_ids)
            spec_obj_internal_keys = set(spec_obj_internal_keys)

            for obj_id in phot_obj_ids:
                self.push(
                    action="skyportal/REFRESH_SOURCE_PHOTOMETRY",
                    payload={"obj_id": obj_id},
                )

            for obj_internal_key in spec_obj_internal_keys:
                self.push(
                    action="skyportal/REFRESH_SOURCE_SPECTRA",
                    payload={"obj_internal_key": obj_internal_key},
                )

            return self.success()
