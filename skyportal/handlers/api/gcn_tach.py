import arrow
import requests
import re
from tornado.ioloop import IOLoop
from ..base import BaseHandler
from baselayer.app.access import auth_or_token, permissions
from ...models import GcnEvent, DBSession
from astropy.time import Time

from baselayer.log import make_log


from sqlalchemy.orm import sessionmaker, scoped_session

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))

log = make_log('api/gcn_aliases')


def get_tach_event_id(dateobs, tags):
    date = dateobs.split("T", 1)[0]
    if 'Neutrino' in tags:
        tags.append('ν')
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
    event_id = None
    for event in events:
        trigger = event["node"]["trigger"]
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
            if event["node"]["date"] == date and event["node"]["evttype"] in tags:
                event_ids.append(event["node"]["id_"])
        if len(event_ids) != 1:
            # multiple events on the same day, cant figure out the right one. We could look at some circular and notices, event types.... to find which one is the right one.
            return None
        event_id = event_ids[0]

    return event_id


def get_aliases(circular_ids, day):
    url = (
        "https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/graphql_fast"
    )
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://heasarc.gsfc.nasa.gov",
    }
    aliases = []
    for id in circular_ids:
        payload = {
            "query": f'''{{
                circularBodyById(id:{id}){{
                    edges{{
                    node{{
                        body
                    }}
                    }}
                }}
            }}'''
        }
        response = requests.request("POST", url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if len(data["data"]["circularBodyById"]["edges"]) > 0:
                body = data["data"]["circularBodyById"]["edges"][0]["node"]["body"]
                pattern = rf"((GRB|IC|S|GW)+\s?({day})([A-Za-z]{{0,2}})?)"
                matches = re.findall(pattern, body)
                matches = (
                    list({match[0].replace(' ', '') for match in matches})
                    if matches is not None
                    else []
                )
                aliases.extend(matches)
    return aliases


def get_tach_event_aliases(id, gcn_event):
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

    circulars = gcn_event.circulars
    # this is a dict with key = circular id and value = title

    aliases = []
    if response.status_code == 200:
        data = response.json()
        if data["data"]["allCirculars"]["totalCount"] > 0:
            events = data["data"]["allCirculars"]["edges"]
            aliases.append(events[0]["node"]["evtidCircular"]["event"].replace(" ", ""))
            new_circulars = {}
            for event in events:
                #     aliases.append(event["node"]["evtidCircular"]["event"].replace(" ", ""))
                if event["node"]["id_"] not in circulars.keys():
                    new_circulars[event["node"]["id_"]] = event["node"]["subject"]
            day = re.sub(r'\D', '', aliases[0])
            aliases = get_aliases(list(new_circulars.keys()), day)
            return aliases, new_circulars
        else:
            return [], {}
    return [], {}


def post_aliases(dateobs, tach_id, user, push_all):
    with Session() as session:
        stmt = GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
        gcn_event = session.scalars(stmt).first()
        if gcn_event is None:
            return
        gcn_event.tach_id = tach_id
        new_gcn_aliases, new_gcn_circulars = get_tach_event_aliases(tach_id, gcn_event)

        if len(new_gcn_aliases) == 0:
            return

        if gcn_event.aliases is None:
            gcn_event.aliases = new_gcn_aliases
        else:
            gcn_aliases = [alias.upper() for alias in gcn_event.aliases]
            for new_gcn_alias in new_gcn_aliases:
                if new_gcn_alias.upper() not in gcn_aliases:
                    gcn_aliases.append(new_gcn_alias)
            gcn_event.aliases = gcn_aliases

        if gcn_event.circulars is None:
            gcn_event.circulars = new_gcn_circulars
        else:
            gcn_event.circulars = {**gcn_event.circulars, **new_gcn_circulars}

        session.commit()

    push_all(
        action='skyportal/REFRESH_GCNEVENT',
        payload={'gcnEvent_dateobs': dateobs},
    )


class GcnTachHandler(BaseHandler):
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
            log(f'Invalid dateobs: {dateobs}')
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
                tach_id = (
                    gcn_event.tach_id
                    if gcn_event.tach_id is not None
                    else get_tach_event_id(dateobs, tags)
                )
                if tach_id is None:
                    return self.error(
                        f'Event {dateobs} not found on TACH, cannot retrieve aliases'
                    )
                gcn_event_id = gcn_event.id

                IOLoop.current().run_in_executor(
                    None,
                    lambda: post_aliases(
                        dateobs, tach_id, session.user_or_token, self.push_all
                    ),
                )

        except Exception as e:
            log(f'Error scraping GCN aliases: {e}')
            return self.error(f'Error: {e}')
        return self.success(data={'id': gcn_event_id})

    @auth_or_token
    def get(self, dateobs):
        # gets the circulars and aliases of a GCN event
        try:
            arrow.get(dateobs).datetime
        except Exception:
            log(f'Invalid dateobs: {dateobs}')
            return self.error(f'Invalid dateobs: {dateobs}')
        try:
            with self.Session() as session:
                stmt = GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
                gcn_event = session.scalars(stmt).first()
                if gcn_event is None:
                    return self.error(f'No GCN event found for {dateobs}')
                tach_id = gcn_event.tach_id
                aliases = gcn_event.aliases
                circulars = gcn_event.circulars

        except Exception as e:
            log(f'Error scraping GCN aliases: {e}')
            return self.error(f'Error: {e}')

        return self.success(
            data={'tach_id': tach_id, 'aliases': aliases, 'circulars': circulars}
        )
