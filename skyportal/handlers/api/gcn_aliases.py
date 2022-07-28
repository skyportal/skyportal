import arrow
from ..base import BaseHandler
from baselayer.app.access import permissions
from ...models import GcnEvent


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

                # here, Leo, will implement his script to scrape other names of this event
                # and save them in the database in GcnEvent.aliases column

                new_gcn_aliases = [
                    'Test name',
                    'GWSomething',
                ]  # HARDCODED. This would be the result of the web scraping. !!!LEO REPLACE THIS BY YOUR CODE!!!

                # here, we need to decide if we replace the current aliases by the new ones, or if we just add names that we didn't have before.
                # we can do this by comparing the two lists.
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
