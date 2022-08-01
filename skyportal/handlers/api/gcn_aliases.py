import arrow
import requests
import re
from bs4 import BeautifulSoup
from ..base import BaseHandler
from baselayer.app.access import permissions
from ...models import GcnEvent

CIRCULARS_URL = "https://gcn.gsfc.nasa.gov/gcn/selected.html"

class GcnAliasesHandler(BaseHandler):
    @permissions(["Manage GCNs"])
    def post(self, dateobs):
        """
        ---
        description: Scrape aliases of a GCN Event from GCNs notice/circulars
        tags:
          - gcn_event
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
            description: The dateobs of the event, as an arrow parseable string
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
                            id:
                              type: int
                              description: The id of the GcnEvent
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            arrow.get(dateobs).datetime
        except Exception:
            return self.error(f'Invalid dateobs: {dateobs}')
        try:
            with self.Session() as session:
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                gcn_event = session.scalars(stmt).first()
                if gcn_event is None:
                    return self.error(f'No GCN event found for {dateobs}')

                split_date = dateobs.split("T", 1)
                date = split_date[0].replace("-", "")[2:]
                time = split_date[1]
                date_pattern = f".*{date}.*"

                all_circulars_page = requests.get(CIRCULARS_URL)
                all_circulars_soup = BeautifulSoup(all_circulars_page.content, "html.parser")
                date_matches = all_circulars_soup.find_all("b", text=re.compile(date_pattern))
                new_gcn_aliases = []
                if date_matches:
                    # Assign A, B, etc
                    for date_match in date_matches:
                        formatted_name = date_match.text.split()[1][:-1]
                        compiled_url = f"https://gcn.gsfc.nasa.gov/gcn/other/{formatted_name}.gcn3"

                        circulars_page = requests.get(compiled_url)
                        if time in circulars_page.text:
                            new_gcn_aliases.append(formatted_name)
                            break

                if gcn_event.aliases is None:
                    gcn_event.aliases = new_gcn_aliases
                else:
                    gcn_aliases = [alias.lower() for alias in gcn_event.aliases]
                    for new_gcn_alias in new_gcn_aliases:
                        if new_gcn_alias.lower() not in gcn_aliases:
                            gcn_aliases.append(new_gcn_alias)
                    gcn_event.aliases = gcn_aliases
                session.commit()
                gcn_event_id = gcn_event.id
        except Exception as e:
            return self.error(f'Error: {e}')
        return self.success(data={'id': gcn_event_id})
