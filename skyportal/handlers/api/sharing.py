from baselayer.app.access import permissions

from ...models import Group, Photometry, Spectrum
from ..base import BaseHandler


class SharingHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self):
        """
        ---
        summary: Share data with additional groups/users
        description: Share data with additional groups/users
        tags:
          - data sharing
          - photometry
          - spectra
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  photometryIDs:
                    type: array
                    items:
                      type: integer
                    description: |
                      IDs of the photometry data to be shared. If `spectrumIDs` is not
                      provided, this is required.
                  spectrumIDs:
                    type: array
                    items:
                      type: integer
                    description: IDs of the spectra to be shared. If `photometryIDs` is
                      not provided, this is required.
                  groupIDs:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups data will be shared with. To share data with
                      a single user, specify their single user group ID here.
                required:
                  - groupIDs
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()
        group_ids = data.get("groupIDs", None)
        if group_ids is None or group_ids == []:
            return self.error("Missing required `groupIDs` field.")
        phot_ids = data.get("photometryIDs", [])
        spec_ids = data.get("spectrumIDs", [])
        if not phot_ids and not spec_ids:
            return self.error(
                "One of either `photometryIDs` or `spectrumIDs` must be provided."
            )

        with self.Session() as session:
            valid_groups = session.scalars(
                Group.select(session.user_or_token)
                .where(Group.id.in_(group_ids))
                .distinct()
            ).all()
            valid_group_ids = [g.id for g in valid_groups]
            invalid_group_ids = [gid for gid in group_ids if gid not in valid_group_ids]

            if len(invalid_group_ids) > 0:
                return self.error(f"Invalid group IDs: {invalid_group_ids}.")
            groups = valid_groups

            phot_obj_ids = []
            spec_obj_internal_keys = []

            if phot_ids:
                valid_phot = session.scalars(
                    Photometry.select(session.user_or_token, mode="update").where(
                        Photometry.id.in_(phot_ids)
                    )
                ).all()
                valid_phot_ids = [op.id for op in valid_phot]
                invalid_phot_ids = [
                    pid for pid in phot_ids if pid not in valid_phot_ids
                ]

                if len(invalid_phot_ids) > 0:
                    return self.error(
                        f"Cannot share photometry IDs {invalid_phot_ids}: not found or you are not the owner."
                    )

                for phot in valid_phot:
                    existing_group_ids = {g.id for g in phot.groups}
                    for group in groups:
                        if group.id not in existing_group_ids:
                            phot.groups.append(group)
                    phot_obj_ids.append(phot.obj_id)

            if spec_ids:
                valid_spec = session.scalars(
                    Spectrum.select(session.user_or_token, mode="update").where(
                        Spectrum.id.in_(spec_ids)
                    )
                ).all()
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

            session.commit()

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
