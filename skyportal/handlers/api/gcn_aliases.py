import arrow
import requests
from ..base import BaseHandler
from baselayer.app.access import permissions
from ...models import GcnEvent
from astropy.time import Time

CIRCULARS_URL = "https://gcn.gsfc.nasa.gov/gcn/selected.html"


def get_tach_event_id(dateobs, tags):
    date = dateobs.split("T", 1)[0]
    url = (
        "https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/graphql_fast"
    )

    payload = {
        "query": f'''{{
              allEventDetails (  date1:\"{date}\" date2:\"{date}\" ) {{
                totalCount
                pageInfo{{
                  hasNextPage
                  hasPreviousPage
                  startCursor
                  endCursor
                }}
                edges {{
                  node {{
                    id
                    id_
                    event
                    evttype
                    trigger
                    ra
                    raHms
                    dec
                    decDms
                    error
                    date
                    circulars
                    notices
                    circnum
                    }}
                  }}
                }}
            }}'''
    }
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://heasarc.gsfc.nasa.gov",
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    data = response.json()
    if response.status_code != 200:
        return None
    if response.json()["data"]["allEventDetails"]["totalCount"] == 0:
        return None

    events = data["data"]["allEventDetails"]["edges"]
    # find the event with the right trigger time
    event_id = None
    for event in events:
        trigger = event["node"]["trigger"]
        # the trigger has the format "YYYY-MM-ddTHH:MM:SS.sss" so we need to round it to the nearest second
        if trigger is not None:
            try:
                trigger = Time(Time(trigger, precision=0).iso).datetime.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
            except Exception:
                continue
            if trigger == dateobs:
                event_id = event["node"]["id_"]

    if event_id is None:
        event_ids = []
        for event in events:
            # this time, there is no trigger so we look at the date
            if event["node"]["date"] == date and event["node"]["evttype"] in tags:
                event_ids.append(event["node"]["id_"])
        if len(event_ids) != 1:
            # multiple events on the same day, cant figure out the right one. We could look at some circular and notices, event types.... to find which one is the right one.
            return None
        event_id = event_ids[0]

    return event_id


def get_tach_event_aliases(id):
    url = "https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/graphql"
    payload = {
        "query": f'''{{
            allCirculars (  evtid:{id} ) {{
              totalCount
              pageInfo{{
                hasNextPage
                hasPreviousPage
                startCursor
                endCursor
              }}
              edges {{
                node {{
                  id
                  id_
                  received
                  subject
                  evtidCircular{{
                    event
                  }}
                  cid
                  evtid
                  oidCircular{{
                    telescope
                    detector
                    oidEvent{{
                      wavelength
                      messenger
                    }}
                  }}
                  }}
                }}
              }}
          }}'''
    }
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://heasarc.gsfc.nasa.gov",
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    aliases = []
    if response.status_code == 200:
        data = response.json()
        if data["data"]["allCirculars"]["totalCount"] > 0:
            events = data["data"]["allCirculars"]["edges"]
            for event in events:
                # for now we just take the event name, which is always the same (the name given to the event in TACH)
                # maybe we could parse the circulars and find the different names used for the same event?
                aliases.append(event["node"]["evtidCircular"]["event"].replace(" ", ""))
            return aliases
        else:
            return []
    return []


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

                tags = gcn_event.tags
                tach_id = get_tach_event_id(dateobs, tags)
                new_gcn_aliases = get_tach_event_aliases(tach_id)

                if gcn_event.aliases is None:
                    gcn_event.aliases = new_gcn_aliases
                else:
                    gcn_aliases = [alias.upper() for alias in gcn_event.aliases]
                    for new_gcn_alias in new_gcn_aliases:
                        if new_gcn_alias.upper() not in gcn_aliases:
                            gcn_aliases.append(new_gcn_alias)
                    gcn_event.aliases = gcn_aliases
                session.commit()
                gcn_event_id = gcn_event.id
        except Exception as e:
            return self.error(f'Error: {e}')
        self.push_all(
            action='skyportal/REFRESH_GCNEVENT',
            payload={'gcnEvent_dateobs': dateobs},
        )
        return self.success(data={'id': gcn_event_id})
