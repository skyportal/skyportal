import requests
from bs4 import BeautifulSoup

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....utils.tns import get_tns_url
from ...base import BaseHandler

log = make_log("api/tns_groups")


class TNSGroupsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        summary: Fetch groups from TNS
        description: |
            Fetch the list of available groups by scraping the
            public TNS groups page.
        tags:
          - tns
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
                            type: object
                            properties:
                              id:
                                type: integer
                              name:
                                type: string
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            groups_url = get_tns_url("groups")
            r = requests.get(
                groups_url, timeout=30, headers={"User-Agent": "SkyPortal"}
            )
            if r.status_code != 200:
                return self.error(
                    f"Failed to fetch TNS groups page (status {r.status_code})."
                )

            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")
            if table is None:
                return self.error("Could not find groups table on TNS groups page.")

            tns_groups = []
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                try:
                    group_id = int(cells[0].get_text(strip=True))
                    group_name = cells[1].get_text(strip=True)
                    if group_name:
                        tns_groups.append({"id": group_id, "name": group_name})
                except (ValueError, TypeError):
                    continue

            tns_groups.sort(key=lambda g: g["name"])
            return self.success(data=tns_groups)

        except Exception as e:
            log(f"Error fetching TNS groups: {e}")
            return self.error("An error occurred while fetching TNS groups.")
