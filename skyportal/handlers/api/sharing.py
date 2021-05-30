from baselayer.app.access import permissions
from ..base import BaseHandler
from ...models import Group, Photometry, Spectrum


class SharingHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: Share data with additional groups/users
        tags:
          - data_sharing
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

        valid_groups = Group.query.filter(Group.id.in_(group_ids))
        valid_group_ids = [g.id for g in valid_groups]
        invalid_group_ids = [gid for gid in group_ids if gid not in valid_group_ids]

        if len(invalid_group_ids) > 0:
            return self.error(f'Invalid group IDs: {invalid_group_ids}.')
        groups = valid_groups

        phot_obj_ids = []
        spec_obj_ids = []

        if phot_ids:
            valid_phot = Photometry.query.filter(Photometry.id.in_(phot_ids))
            valid_phot_ids = [op.id for op in valid_phot]
            invalid_phot_ids = [pid for pid in phot_ids if pid not in valid_phot_ids]

            if len(invalid_phot_ids) > 0:
                return self.error(f'Invalid photometry IDs: {invalid_phot_ids}.')

            for phot in valid_phot:
                # Ensure user has access to data being shared
                if (
                    phot.owner_id != self.associated_user_object.id
                    and "System admin" not in self.current_user.permissions
                ):
                    return self.error(
                        f"Cannot share photometry id {phot.id}: you are not the owner of this point."
                    )
                for group in groups:
                    phot.groups.append(group)
                # Grab obj_id for use in websocket message below
                phot_obj_ids.append(phot.obj_id)

        if spec_ids:
            valid_spec = Spectrum.query.filter(Spectrum.id.in_(spec_ids))
            valid_spec_ids = [os.id for os in valid_spec]
            invalid_spec_ids = [sid for sid in spec_ids if sid not in valid_spec_ids]

            if len(invalid_spec_ids) > 0:
                return self.error(f'Invalid spectrum IDs: {invalid_spec_ids}.')

            for spec in valid_spec:
                # Ensure user has access to data being shared
                if (
                    spec.owner_id != self.associated_user_object.id
                    and "System admin" not in self.current_user.permissions
                ):
                    return self.error(
                        f"Cannot share spectrum id {phot.id}: you are not the owner of this spectrum."
                    )
                for group in groups:
                    spec.groups.append(group)
                # Grab obj_id for use in websocket message below
                spec_obj_ids.append(spec.obj_id)

        self.verify_and_commit()

        spec_obj_ids = set(spec_obj_ids)
        phot_obj_ids = set(phot_obj_ids)
        for obj_id in phot_obj_ids:
            self.push(
                action="skyportal/FETCH_SOURCE_PHOTOMETRY", payload={"obj_id": obj_id}
            )

        for obj_id in spec_obj_ids:
            self.push(
                action="skyportal/FETCH_SOURCE_SPECTRA", payload={"obj_id": obj_id}
            )

        return self.success()
