import io
import arrow
from astropy.time import Time, TimeDelta
import astropy.units as u
import numpy as np
import obspy
from obspy.geodetics.base import gps2dist_azimuth
from obspy.taup import TauPyModel
from obspy.taup.helper_classes import TauModelError
import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token
from baselayer.app.custom_exceptions import AccessError
from baselayer.log import make_log

from ..base import BaseHandler
from ...models import (
    EarthquakeEvent,
    EarthquakeMeasured,
    EarthquakeNotice,
    EarthquakePrediction,
    MMADetector,
    User,
)
from ...utils.earthquake import (
    get_country,
)

log = make_log('earthquake')


def post_earthquake_from_xml(payload, user_id, session):
    """Post Earthquake to database from quakeml xml.
    payload: str
         readable string
    user_id : int
        SkyPortal ID of User posting the Earthquake
    session: sqlalchemy.Session
        Database session for this transaction
    """

    user = session.query(User).get(user_id)

    event = obspy.core.event.read_events(io.StringIO(payload), format="QUAKEML")[0]
    event_uri = event.resource_id.id.replace("/", "-")

    split_strings = ["1-query?eventid=", "-EVENT-", "-Event-", "-event-", "-geofon-"]
    event_id = None
    for split_string in split_strings:
        str_split = event_uri.split(split_string)
        if len(str_split) > 1:
            event_id = str_split[-1]
            break
    if event_id is None:
        event_id = event_uri

    event_type = event.event_type
    if event_type == "not existing":
        event = session.scalars(
            EarthquakeEvent.select(user, mode="update").where(
                EarthquakeEvent.event_id == event_id
            )
        ).first()
        if event is not None:
            event.status = 'canceled'
            session.add(event)
            session.commit()

            return event.id
        else:
            return None

    magnitudes = event.magnitudes
    if len(magnitudes) == 0:
        raise ValueError('Must have magnitude information to create Earthquake.')

    mag = magnitudes[-1].mag
    origin = event.origins[-1]

    event = session.scalars(
        EarthquakeEvent.select(user).where(EarthquakeEvent.event_id == event_id)
    ).first()

    if event is None:
        event = EarthquakeEvent(
            event_id=event_id, event_uri=event_uri, sent_by_id=user.id
        )
        session.add(event)
    else:
        if not event.is_accessible_by(user, mode="update"):
            raise AccessError(
                "Insufficient permissions: Earthquake event can only be updated by original poster"
            )

    country = get_country(origin.latitude, origin.longitude)
    earthquake_notice = EarthquakeNotice(
        content=payload.encode('utf-8'),
        event_id=event_id,
        lat=origin.latitude,
        lon=origin.longitude,
        depth=origin.depth,
        magnitude=mag,
        country=country,
        date=origin.time.datetime,
        sent_by_id=user.id,
    )
    session.add(earthquake_notice)
    session.commit()

    return event_id


def post_earthquake_from_dictionary(payload, user_id, session):
    """Post Earthquake to database from dictionary.
    payload: dict
        Dictionary containing date, location, and magnitude information
    user_id : int
        SkyPortal ID of User posting the Earthquake
    session: sqlalchemy.Session
        Database session for this transaction
    """

    user = session.query(User).get(user_id)

    date = payload['date']
    event_id = payload['event_id']
    latitude = payload['latitude']
    longitude = payload['longitude']
    depth = payload['depth']
    magnitude = payload['magnitude']

    event = session.scalars(
        EarthquakeEvent.select(user).where(EarthquakeEvent.event_id == event_id)
    ).first()

    if event is None:
        event = EarthquakeEvent(event_id=event_id, sent_by_id=user.id)
        session.add(event)
    else:
        if not event.is_accessible_by(user, mode="update"):
            raise ValueError(
                "Insufficient permissions: Earthquake event can only be updated by original poster"
            )

    country = get_country(latitude, longitude)
    earthquake_notice = EarthquakeNotice(
        event_id=event_id,
        lat=latitude,
        lon=longitude,
        depth=depth,
        magnitude=magnitude,
        country=country,
        date=date,
        sent_by_id=user.id,
    )
    session.add(earthquake_notice)
    session.commit()

    return event_id


class EarthquakeStatusHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Get all Earthquake status tags
        tags:
          - earthquakeevents
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            statuses = (
                session.scalars(sa.select(EarthquakeEvent.status).distinct())
                .unique()
                .all()
            )
            return self.success(data=statuses)


class EarthquakeHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Ingest EarthquakeEvent
        tags:
          - earthquakeevents
          - earthquakenotices
        requestBody:
          content:
            application/json:
              schema: EarthquakeEventNoID
        responses:
          200:
            content:
              application/json:
                schema: Success
                properties:
                  data:
                    type: object
                    properties:
                      gcnevent_id:
                        type: integer
                        description: New Earthquake ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        if 'xml' not in data:
            required_keys = {
                'date',
                'event_id',
                'latitude',
                'longitude',
                'depth',
                'magnitude',
            }
            if not required_keys.issubset(set(data.keys())):
                return self.error(
                    "Either xml or (event_id, latitude, longitude, depth, magnitude) must be present in data to parse EarthquakeEvent"
                )

        with self.Session() as session:
            if 'xml' in data:
                event_id = post_earthquake_from_xml(
                    data['xml'], self.associated_user_object.id, session
                )
            else:
                event_id = post_earthquake_from_dictionary(
                    data, self.associated_user_object.id, session
                )

            return self.success(data={'id': event_id})

    @auth_or_token
    async def get(self, event_id=None):
        """
        ---
        single:
          description: Retrieve an Earthquake event
          tags:
            - earthquakeevents
          parameters:
            - in: path
              name: event_id
              required: false
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleEarthquakeEvent
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve multiple Earthquake events
          tags:
            - earthquakeevents
          parameters:
            - in: query
              name: startDate
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
                date >= startDate
            - in: query
              name: endDate
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
                date <= endDate
            - in: query
              name: statusKeep
              nullable: true
              schema:
                type: string
              description: |
                Earthquake Status to match against
            - in: query
              name: statusRemove
              nullable: true
              schema:
                type: string
              description: |
                Earthquake Status to filter out
            - in: query
              name: numPerPage
              nullable: true
              schema:
                type: integer
              description: |
                Number of earthquakes. Defaults to 100.
            - in: query
              name: pageNumber
              nullable: true
              schema:
                type: integer
              description: Page number for iterating through all earthquakes. Defaults to 1

        responses:
          200:
            content:
              application/json:
                schema: ArrayOfEarthquakeEvents
          400:
            content:
              application/json:
                schema: Error
        """

        page_number = self.get_query_argument("pageNumber", 1)
        try:
            page_number = int(page_number)
        except ValueError as e:
            return self.error(f'pageNumber fails: {e}')

        n_per_page = self.get_query_argument("numPerPage", 100)
        try:
            n_per_page = int(n_per_page)
        except ValueError as e:
            return self.error(f'numPerPage fails: {e}')

        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        status_keep = self.get_query_argument('statusKeep', None)
        status_remove = self.get_query_argument('statusRemove', None)

        if event_id is not None:
            with self.Session() as session:
                event = session.scalars(
                    EarthquakeEvent.select(
                        session.user_or_token,
                        options=[
                            joinedload(EarthquakeEvent.notices).undefer(
                                EarthquakeNotice.content
                            ),
                            joinedload(EarthquakeEvent.comments),
                            joinedload(EarthquakeEvent.predictions),
                            joinedload(EarthquakeEvent.measurements),
                        ],
                    ).where(EarthquakeEvent.event_id == event_id)
                ).first()
                if event is None:
                    return self.error("Earthquake event not found", status=404)

                data = {
                    **event.to_dict(),
                    "notices": sorted(
                        (notice.to_dict() for notice in event.notices),
                        key=lambda x: x["created_at"],
                        reverse=True,
                    ),
                    "predictions": sorted(
                        (prediction.to_dict() for prediction in event.predictions),
                        key=lambda x: x["created_at"],
                        reverse=True,
                    ),
                    "comments": sorted(
                        (
                            {
                                **{
                                    k: v
                                    for k, v in c.to_dict().items()
                                    if k != "attachment_bytes"
                                },
                                "author": {
                                    **c.author.to_dict(),
                                    "gravatar_url": c.author.gravatar_url,
                                },
                                "resourceType": "earthquake",
                            }
                            for c in event.comments
                        ),
                        key=lambda x: x["created_at"],
                        reverse=True,
                    ),
                }

                return self.success(data=data)

        with self.Session() as session:

            query = EarthquakeEvent.select(
                session.user_or_token,
                options=[
                    joinedload(EarthquakeEvent.notices),
                ],
            )

            if start_date:
                start_date = arrow.get(start_date.strip()).datetime
                notice_subquery = (
                    EarthquakeNotice.select(session.user_or_token)
                    .where(EarthquakeNotice.date >= start_date)
                    .subquery()
                )
                query = query.join(
                    notice_subquery,
                    EarthquakeEvent.event_id == notice_subquery.c.event_id,
                )
            if end_date:
                end_date = arrow.get(end_date.strip()).datetime

                notice_subquery = (
                    EarthquakeNotice.select(session.user_or_token)
                    .where(EarthquakeNotice.date <= end_date)
                    .subquery()
                )
                query = query.join(
                    notice_subquery,
                    EarthquakeEvent.event_id == notice_subquery.c.event_id,
                )

            if status_keep:
                query = query.where(EarthquakeEvent.status.contains(status_keep))
            if status_remove:
                query = query.where(~EarthquakeEvent.status.contains(status_remove))

            total_matches = session.scalar(
                sa.select(sa.func.count()).select_from(query)
            )

            if n_per_page is not None:
                query = (
                    query.distinct()
                    .limit(n_per_page)
                    .offset((page_number - 1) * n_per_page)
                )

            events = []
            for event in session.scalars(query).unique().all():
                events.append({**event.to_dict(), "notices": list(set(event.notices))})

            query_results = {"events": events, "totalMatches": int(total_matches)}

            return self.success(data=query_results)

    @auth_or_token
    def delete(self, event_id):
        """
        ---
        description: Delete an Earthquake event
        tags:
          - earthquakeevents
        parameters:
          - in: path
            name: event_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        with self.Session() as session:
            event = session.scalars(
                EarthquakeEvent.select(session.user_or_token, mode="delete").where(
                    EarthquakeEvent.event_id == event_id
                )
            ).first()
            if event is None:
                return self.error("Earthquake event not found", status=404)

            session.delete(event)
            session.commit()

            return self.success()


class EarthquakePredictionHandler(BaseHandler):
    @auth_or_token
    async def post(self, earthquake_id, mma_detector_id):
        """
        ---
        description: Perform a prediction analysis for the earthquake.
        tags:
          - earthquakeevents
        parameters:
          - in: path
            name: earthquake_id
            required: true
            schema:
              type: string
          - in: path
            name: mma_detector_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            event = session.scalars(
                EarthquakeEvent.select(
                    session.user_or_token,
                    options=[
                        joinedload(EarthquakeEvent.notices),
                    ],
                ).where(EarthquakeEvent.event_id == earthquake_id)
            ).first()
            if event is None:
                return self.error(
                    f'Cannot find EarthquakeEvent with ID {earthquake_id}'
                )

            detector = session.scalars(
                MMADetector.select(session.user_or_token).where(
                    MMADetector.id == mma_detector_id
                )
            ).first()
            if detector is None:
                return self.error(f'Cannot find MMADetector with ID {mma_detector_id}')

            notices = event.notices
            if len(notices) == 0:
                return self.error('Cannot make prediction with no information.')
            notice = notices[-1]

            if not detector.fixed_location:
                return self.error(
                    'Cannot make prediction for a detector not at a fixed location.'
                )

            (
                Dist,
                Ptime,
                Stime,
                Rtwotime,
                RthreePointFivetime,
                Rfivetime,
            ) = compute_traveltimes(notice, detector)

            # FIXME : Add code for amplitude and lockloss prediction
            Rfamp, Lockloss = 0.0, 0.0

            prediction = EarthquakePrediction(
                event_id=event.id,
                detector_id=detector.id,
                d=Dist,
                p=Ptime,
                s=Stime,
                r2p0=Rtwotime,
                r3p5=RthreePointFivetime,
                r5p0=Rfivetime,
                rfamp=Rfamp,
                lockloss=Lockloss,
            )
            session.add(prediction)
            session.commit()

            self.push(
                action="skyportal/REFRESH_EARTHQUAKE",
                payload={"earthquake_event_id": event.event_id},
            )

            return self.success()


def compute_traveltimes(earthquake, detector):
    """Compute earthquake properties

    Parameters
    ----------
    earthquake : skymodel.models.earthquake.EarthquakeEvent
        EarthquakeEvent to compute parameters for
    detector : skymodel.models.mmadetector.MMADetector
        MMA Detector to compute parameters for
    """

    depth = earthquake.depth
    eqtime = Time(earthquake.date, format='datetime')
    eqlat = earthquake.lat
    eqlon = earthquake.lon
    ifolat = detector.lat
    ifolon = detector.lon

    distance, fwd, back = gps2dist_azimuth(eqlat, eqlon, ifolat, ifolon)
    Dist = distance / 1000
    degree = (distance / 6370000) * (180 / np.pi)

    model = TauPyModel(model="iasp91")

    Rtwotime = eqtime + TimeDelta(distance / 2000.0 * u.s)
    RthreePointFivetime = eqtime + TimeDelta(distance / 3500.0 * u.s)
    Rfivetime = eqtime + TimeDelta(distance / 5000.0 * u.s)

    try:
        arrivals = model.get_travel_times(
            source_depth_in_km=depth, distance_in_degree=degree
        )

        Ptime = -1
        Stime = -1
        for phase in arrivals:
            if Ptime == -1 and phase.name.lower()[0] == "p":
                Ptime = eqtime + TimeDelta(phase.time * u.s)
            if Stime == -1 and phase.name.lower()[0] == "s":
                Stime = eqtime + TimeDelta(phase.time * u.s)
    except TauModelError:
        Ptime, Stime = Rtwotime, Rtwotime

    return (
        Dist,
        Ptime.datetime,
        Stime.datetime,
        Rtwotime.datetime,
        RthreePointFivetime.datetime,
        Rfivetime.datetime,
    )


class EarthquakeMeasurementHandler(BaseHandler):
    @auth_or_token
    async def post(self, earthquake_id, mma_detector_id):
        """
        ---
        description: Provide a ground velocity measurement for the earthquake.
        tags:
          - earthquakeevents
        parameters:
          - in: path
            name: earthquake_id
            required: true
            schema:
              type: string
          - in: path
            name: mma_detector_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        data = self.get_json()
        if 'rfamp' not in data and 'lockloss' not in data:
            return self.error(
                'Need to provide at least one of rfamp or lockloss measurement'
            )

        with self.Session() as session:
            event = session.scalars(
                EarthquakeEvent.select(
                    session.user_or_token,
                ).where(EarthquakeEvent.event_id == earthquake_id)
            ).first()
            if event is None:
                return self.error(
                    f'Cannot find EarthquakeEvent with ID {earthquake_id}'
                )

            detector = session.scalars(
                MMADetector.select(session.user_or_token).where(
                    MMADetector.id == mma_detector_id
                )
            ).first()
            if detector is None:
                return self.error(f'Cannot find MMADetector with ID {mma_detector_id}')

            measurement = session.scalars(
                EarthquakeMeasured.select(session.user_or_token).where(
                    EarthquakeMeasured.id == event.id,
                    EarthquakeMeasured.detector_id == detector.id,
                )
            ).first()
            if measurement is not None:
                return self.error(
                    'Measurement for this earthquake and detector already exists. Please patch that measurement if an update is required'
                )

            rfamp = data.get('rfamp', None)
            lockloss = data.get('lockloss', None)

            measurement = EarthquakeMeasured(
                event_id=event.id,
                detector_id=detector.id,
                rfamp=rfamp,
                lockloss=lockloss,
            )
            session.add(measurement)
            session.commit()

            self.push(
                action="skyportal/REFRESH_EARTHQUAKE",
                payload={"earthquake_id": earthquake_id},
            )

            return self.success()

    @auth_or_token
    async def get(self, earthquake_id, mma_detector_id):
        """
        ---
        description: Retrieve a ground velocity measurement for the earthquake.
        tags:
          - earthquakeevents
        parameters:
          - in: path
            name: earthquake_id
            required: true
            schema:
              type: string
          - in: path
            name: mma_detector_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: SingleEarthquakeMeasured
        """

        with self.Session() as session:
            event = session.scalars(
                EarthquakeEvent.select(
                    session.user_or_token,
                ).where(EarthquakeEvent.event_id == earthquake_id)
            ).first()
            if event is None:
                return self.error(
                    f'Cannot find EarthquakeEvent with ID {earthquake_id}'
                )

            measurement = session.scalars(
                EarthquakeMeasured.select(session.user_or_token).where(
                    EarthquakeMeasured.event_id == event.id,
                    EarthquakeMeasured.detector_id == mma_detector_id,
                )
            ).first()
            if measurement is None:
                return self.error(
                    'Measurement for this earthquake and detector not found.'
                )

            return self.success(data=measurement)

    @auth_or_token
    async def patch(self, earthquake_id, mma_detector_id):
        """
        ---
        description: Update a ground velocity measurement for the earthquake.
        tags:
          - earthquakeevents
        parameters:
          - in: path
            name: earthquake_id
            required: true
            schema:
              type: string
          - in: path
            name: mma_detector_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        data = self.get_json()
        if 'rfamp' not in data and 'lockloss' not in data:
            return self.error(
                'Need to provide at least one of rfamp or lockloss measurement'
            )

        with self.Session() as session:
            event = session.scalars(
                EarthquakeEvent.select(
                    session.user_or_token,
                ).where(EarthquakeEvent.event_id == earthquake_id)
            ).first()
            if event is None:
                return self.error(
                    f'Cannot find EarthquakeEvent with ID {earthquake_id}'
                )

            measurement = session.scalars(
                EarthquakeMeasured.select(session.user_or_token, mode='update').where(
                    EarthquakeMeasured.event_id == event.id,
                    EarthquakeMeasured.detector_id == mma_detector_id,
                )
            ).first()
            if measurement is None:
                return self.error(
                    'Measurement for this earthquake and detector not found.'
                )

            rfamp = data.get('rfamp', None)
            lockloss = data.get('lockloss', None)

            if rfamp is not None:
                measurement.rfamp = rfamp
            if lockloss is not None:
                measurement.lockloss = lockloss

            session.add(measurement)
            session.commit()

            self.push(
                action="skyportal/REFRESH_EARTHQUAKE",
                payload={"earthquake_id": earthquake_id},
            )

            return self.success()

    @auth_or_token
    async def delete(self, earthquake_id, mma_detector_id):
        """
        ---
        description: Delete a ground velocity measurement for the earthquake.
        tags:
          - earthquakeevents
        parameters:
          - in: path
            name: earthquake_id
            required: true
            schema:
              type: string
          - in: path
            name: mma_detector_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            event = session.scalars(
                EarthquakeEvent.select(
                    session.user_or_token,
                ).where(EarthquakeEvent.event_id == earthquake_id)
            ).first()
            if event is None:
                return self.error(
                    f'Cannot find EarthquakeEvent with ID {earthquake_id}'
                )

            measurement = session.scalars(
                EarthquakeMeasured.select(session.user_or_token, mode='delete').where(
                    EarthquakeMeasured.event_id == event.id,
                    EarthquakeMeasured.detector_id == mma_detector_id,
                )
            ).first()
            if measurement is None:
                return self.error(
                    'Measurement for this earthquake and detector not found.'
                )

            session.delete(measurement)
            session.commit()

            self.push(
                action="skyportal/REFRESH_EARTHQUAKE",
                payload={"earthquake_id": earthquake_id},
            )

            return self.success()
