from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Group, Photometry, Spectrum


class SharingHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Share data with additional groups/users
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
            return self.error("One of either `photometryIDs` or `spectrumIDs` "
                              "must be provided.")
        groups = Group.query.filter(Group.id.in_(group_ids))
        if not all([group in self.current_user.accessible_groups for group in groups]):
            return self.error("Insufficient permissions: you must have access to each "
                              "target group you wish to share data with.")
        obj_id = None
        if phot_ids:
            query = Photometry.query.filter(Photometry.id.in_(phot_ids))
            for phot in query:
                # Ensure user has access to data being shared
                _ = Photometry.get_if_owned_by(phot.id, self.current_user)
                for group in groups:
                    phot.groups.append(group)
                # Grab obj_id for use in websocket message below
                if obj_id is None:
                    obj_id = phot.obj_id
        if spec_ids:
            query = Spectrum.query.filter(Spectrum.id.in_(spec_ids))
            for spec in query:
                # Ensure user has access to data being shared
                _ = Spectrum.get_if_owned_by(spec.id, self.current_user)
                for group in groups:
                    spec.groups.append(group)
                # Grab obj_id for use in websocket message below
                if obj_id is None:
                    obj_id = spec.obj_id
        DBSession().commit()
        if phot_ids:
            self.push(action="skyportal/FETCH_SOURCE_PHOTOMETRY",
                      payload={"obj_id": obj_id})
        if spec_ids:
            self.push(action="skyportal/FETCH_SOURCE_SPECTRA",
                      payload={"obj_id": obj_id})
        return self.success()
