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
        if phot_ids:
            query = Photometry.query.filter(Photometry.id.in_(phot_ids))
            groups = Group.query.filter(Group.id.in_(group_ids))
            for phot in query:
                for group in groups:
                    phot.groups.append(group)
        if spec_ids:
            query = Spectrum.query.filter(Spectrum.id.in_(spec_ids))
            groups = Group.query.filter(Group.id.in_(group_ids))
            for spec in query:
                for group in groups:
                    spec.groups.append(group)
        DBSession().commit()
        return self.success()
