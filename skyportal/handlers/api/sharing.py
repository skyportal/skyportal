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
                  dataType:
                    type: string
                    description: The class name of the data type to be shared
                    enum: [Photometry, Spectrum]
                  IDs:
                    type: array
                    items:
                      type: integer
                    description: IDs of the data to be shared.
                  groupIDs:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups data will be shared with. To share data with
                      a single user, specify their single user group ID here.
                required:
                  - dataType
                  - IDs
                  - groupIDs
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()
        data_type = data.get("dataType", None)
        if data_type is None:
            return self.error("Missing required `dataType` field.")
        group_ids = data.get("groupIDs", None)
        if group_ids is None or group_ids == []:
            return self.error("Missing required `groupIDs` field.")
        ids = data.get("IDs", None)
        if ids is None or ids == []:
            return self.error("Missing required `IDs` field.")
        if data_type == "Photometry":
            data_class = Photometry
        elif data_type == "Spectrum":
            data_class = Spectrum
        else:
            return self.error(f"Invalid `dataType` value provided: {data_type}")
        query = data_class.query.filter(data_class.id.in_(ids))
        groups = Group.query.filter(Group.id.in_(group_ids))
        for record in query:
            for group in groups:
                record.groups.append(group)
        DBSession().commit()
        return self.success()
