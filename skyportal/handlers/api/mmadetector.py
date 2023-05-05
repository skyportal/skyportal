import arrow
from arrow import ParserError

from sqlalchemy.orm import joinedload
from sqlalchemy import or_

from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.custom_exceptions import AccessError

from .spectrum import parse_id_list
from ..base import BaseHandler
from ...models import MMADetector, MMADetectorSpectrum, MMADetectorTimeInterval, Group

from ...models.schema import (
    MMADetectorSpectrumPost,
)


class MMADetectorHandler(BaseHandler):
    @permissions(['Manage allocations'])
    def post(self):
        """
        ---
        description: Create a Multimessenger Astronomical Detector (MMADetector)
        tags:
          - mmadetectors
        requestBody:
          content:
            application/json:
              schema: MMADetectorNoID
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
                              type: integer
                              description: New mmadetector ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()

        with self.Session() as session:

            schema = MMADetector.__schema__()
            try:
                mmadetector = schema.load(data)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )
            if data['fixed_location']:
                if (
                    data['lat'] < -90
                    or data['lat'] > 90
                    or data['lon'] < -180
                    or data['lon'] > 180
                ):
                    return self.error(
                        'Latitude must be between -90 and 90, longitude between -180 and 180'
                    )
            session.add(mmadetector)
            session.commit()

            self.push_all(action="skyportal/REFRESH_MMADETECTOR_LIST")
            return self.success(data={"id": mmadetector.id})

    @auth_or_token
    def get(self, mmadetector_id=None):
        """
        ---
        single:
          description: Retrieve a Multimessenger Astronomical Detector (MMADetector)
          tags:
            - mmadetectors
          parameters:
            - in: path
              name: mmadetector_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleMMADetector
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all Multimessenger Astronomical Detectors (MMADetectors)
          tags:
            - mmadetectors
          parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by name
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfMMADetectors
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:

            if mmadetector_id is not None:
                t = session.scalars(
                    MMADetector.select(
                        session.user_or_token, options=[joinedload(MMADetector.events)]
                    ).where(MMADetector.id == int(mmadetector_id))
                ).first()
                if t is None:
                    return self.error(
                        f"Could not load MMA Detector with ID {mmadetector_id}"
                    )
                return self.success(data=t)

            det_name = self.get_query_argument("name", None)
            stmt = MMADetector.select(session.user_or_token)
            if det_name is not None:
                stmt = stmt.where(MMADetector.name.contains(det_name))

            data = session.scalars(stmt).all()
            return self.success(data=data)

    @permissions(['Manage allocations'])
    def patch(self, mmadetector_id):
        """
        ---
        description: Update a Multimessenger Astronomical Detector (MMADetector)
        tags:
          - mmadetectors
        parameters:
          - in: path
            name: mmadetector_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: MMADetectorNoID
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
            t = session.scalars(
                MMADetector.select(session.user_or_token, mode="update").where(
                    MMADetector.id == int(mmadetector_id)
                )
            ).first()
            if t is None:
                return self.error('Invalid MMA Detector ID.')
            data = self.get_json()
            data['id'] = int(mmadetector_id)

            schema = MMADetector.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )

            if 'name' in data:
                t.name = data['name']
            if 'nickname' in data:
                t.nickname = data['nickname']
            if 'lat' in data:
                if data['lat'] < -90 or data['lat'] > 90:
                    return self.error('Latitude must be between -90 and 90')
                t.lat = data['lat']
            if 'lon' in data:
                if data['lon'] < -180 or data['lon'] > 180:
                    return self.error('Longitude between -180 and 180')
                t.lon = data['lon']
            if 'fixed_location' in data:
                t.fixed_location = data['fixed_location']
            if 'type' in data:
                t.type = data['type']

            session.commit()

            self.push_all(action="skyportal/REFRESH_MMADETECTOR_LIST")
            return self.success()

    @permissions(['Manage allocations'])
    def delete(self, mmadetector_id):
        """
        ---
        description: Delete a Multimessenger Astronomical Detector (MMADetector)
        tags:
          - mmadetectors
        parameters:
          - in: path
            name: mmadetector_id
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
            t = session.scalars(
                MMADetector.select(session.user_or_token, mode="delete").where(
                    MMADetector.id == int(mmadetector_id)
                )
            ).first()
            if t is None:
                return self.error('Invalid MMA Detector ID.')
            session.delete(t)
            session.commit()
            self.push_all(action="skyportal/REFRESH_MMADETECTOR_LIST")
            return self.success()


class MMADetectorSpectrumHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload a Multimessenger Astronomical Detector (MMADetector) spectrum
        tags:
          - mmadetector_spectra
        requestBody:
          content:
            application/json:
              schema: MMADetectorSpectrumPost
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
                              type: integer
                              description: New mmadetector spectrum ID
          400:
            content:
              application/json:
                schema: Error
        """
        json = self.get_json()
        try:
            data = MMADetectorSpectrumPost.load(json)
        except ValidationError as e:
            return self.error(
                f'Invalid / missing parameters; {e.normalized_messages()}'
            )

        with self.Session() as session:
            stmt = MMADetector.select(self.current_user).where(
                MMADetector.id == data['detector_id']
            )
            mmadetector = session.scalars(stmt).first()
            if mmadetector is None:
                return self.error(
                    f'Cannot find mmadetector with ID: {data["detector_id"]}'
                )

            owner_id = self.associated_user_object.id

            # always append the single user group
            single_user_group = self.associated_user_object.single_user_group

            group_ids = data.pop("group_ids", None)
            if group_ids == [] or group_ids is None:
                group_ids = [single_user_group.id]
            elif group_ids == "all":
                group_ids = [g.id for g in self.current_user.accessible_groups]

            if single_user_group.id not in group_ids:
                group_ids.append(single_user_group.id)

            groups = (
                session.scalars(
                    Group.select(self.current_user).where(Group.id.in_(group_ids))
                )
                .unique()
                .all()
            )
            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.'
                )

            spec = MMADetectorSpectrum(**data)
            spec.mmadetector = mmadetector
            spec.groups = groups
            spec.owner_id = owner_id
            session.add(spec)

            session.commit()

            self.push_all(
                action='skyportal/REFRESH_MMADETECTOR',
                payload={'detector_id': spec.detector.id},
            )

            self.push_all(
                action='skyportal/REFRESH_MMADETECTOR_SPECTRA',
                payload={'detector_id': spec.detector.id},
            )

            return self.success(data={"id": spec.id})

    @auth_or_token
    def get(self, spectrum_id=None):
        """
        ---
        single:
          description: Retrieve an mmadetector spectrum
          tags:
            - mmadetector_spectra
          parameters:
            - in: path
              name: spectrum_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleMMADetectorSpectrum
            403:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve multiple spectra with given criteria
          tags:
            - mmadetector_spectra
          parameters:
            - in: query
              name: observedBefore
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided,
                return only spectra observed before this time.
            - in: query
              name: observedAfter
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided,
                return only spectra observed after this time.
            - in: query
              name: detectorIDs
              nullable: true
              type: list
              items:
                type: integer
              description: |
                If provided, filter only spectra observed with one of these mmadetector IDs.
            - in: query
              name: groupIDs
              nullable: true
              schema:
                type: list
                items:
                  type: integer
              description: |
                If provided, filter only spectra saved to one of these group IDs.
        """

        if spectrum_id is not None:
            with self.Session() as session:
                spectrum = session.scalars(
                    MMADetectorSpectrum.select(session.user_or_token).where(
                        MMADetectorSpectrum.id == spectrum_id
                    )
                ).first()
                if spectrum is None:
                    return self.error(
                        f'Could not access spectrum {spectrum_id}.', status=403
                    )
                return self.success(data=spectrum)

        # multiple spectra
        observed_before = self.get_query_argument('observedBefore', None)
        observed_after = self.get_query_argument('observedAfter', None)
        detector_ids = self.get_query_argument('detectorIDs', None)
        group_ids = self.get_query_argument('groupIDs', None)

        # validate inputs
        try:
            observed_before = (
                arrow.get(observed_before).datetime if observed_before else None
            )
        except (TypeError, ParserError):
            return self.error(f'Cannot parse time input value "{observed_before}".')

        try:
            observed_after = (
                arrow.get(observed_after).datetime if observed_after else None
            )
        except (TypeError, ParserError):
            return self.error(f'Cannot parse time input value "{observed_after}".')

        with self.Session() as session:

            try:
                detector_ids = parse_id_list(detector_ids, MMADetector, session)
                group_ids = parse_id_list(group_ids, Group, session)
            except (ValueError, AccessError) as e:
                return self.error(str(e))

            # filter the spectra
            spec_query = MMADetectorSpectrum.select(session.user_or_token)
            if detector_ids:
                spec_query = spec_query.where(
                    MMADetectorSpectrum.detector_id.in_(detector_ids)
                )

            if group_ids:
                spec_query = spec_query.where(
                    or_(
                        *[
                            MMADetectorSpectrum.groups.any(Group.id == gid)
                            for gid in group_ids
                        ]
                    )
                )

            if observed_before:
                spec_query = spec_query.where(
                    MMADetectorSpectrum.end_time <= observed_before
                )

            if observed_after:
                spec_query = spec_query.where(
                    MMADetectorSpectrum.start_time >= observed_after
                )

            spectra = session.scalars(spec_query).unique().all()

            return self.success(data=spectra)

    @permissions(['Upload data'])
    def patch(self, spectrum_id):
        """
        ---
        description: Update mmadetector spectrum
        tags:
          - mmadetector_spectra
        parameters:
          - in: path
            name: spectrum_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: MMADetectorSpectrumPost
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

        try:
            spectrum_id = int(spectrum_id)
        except TypeError:
            return self.error('Could not convert spectrum id to int.')

        data = self.get_json()

        try:
            data = MMADetectorSpectrumPost.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )

        group_ids = data.pop("group_ids", None)
        if group_ids == 'all':
            group_ids = [g.id for g in self.current_user.accessible_groups]

        with self.Session() as session:
            stmt = MMADetectorSpectrum.select(self.current_user).where(
                MMADetectorSpectrum.id == spectrum_id
            )
            spectrum = session.scalars(stmt).first()

            if group_ids:
                groups = (
                    session.scalars(
                        Group.select(self.current_user).where(Group.id.in_(group_ids))
                    )
                    .unique()
                    .all()
                )
                if {g.id for g in groups} != set(group_ids):
                    return self.error(
                        f'Cannot find one or more groups with IDs: {group_ids}.'
                    )

                if groups:
                    spectrum.groups = spectrum.groups + groups

            for k in data:
                setattr(spectrum, k, data[k])

            session.commit()

            self.push_all(
                action='skyportal/REFRESH_MMADETECTOR',
                payload={'detector_id': spectrum.detector.id},
            )

            self.push_all(
                action='skyportal/REFRESH_MMADETECTOR_SPECTRA',
                payload={'detector_id': spectrum.detector.id},
            )

            return self.success()

    @permissions(['Upload data'])
    def delete(self, spectrum_id):
        """
        ---
        description: Delete an mmadetector spectrum
        tags:
          - mmadetector_spectra
        parameters:
          - in: path
            name: spectrum_id
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
            spectrum = session.scalars(
                MMADetectorSpectrum.select(self.current_user, mode="delete").where(
                    MMADetectorSpectrum.id == spectrum_id
                )
            ).first()
            if spectrum is None:
                return self.error(f'Cannot find spectrum with ID {spectrum_id}')

            detector_id = spectrum.detector.id
            session.delete(spectrum)
            session.commit()

            self.push_all(
                action='skyportal/REFRESH_MMADETECTOR',
                payload={'detector_id': detector_id},
            )

            self.push_all(
                action='skyportal/REFRESH_MMADETECTOR_SPECTRA',
                payload={'detector_id': detector_id},
            )

            return self.success()


class MMADetectorTimeIntervalHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload a Multimessenger Astronomical Detector (MMADetector) time_interval(s)
        tags:
          - mmadetector_time_intervals
        requestBody:
          content:
            application/json:
              schema: MMADetectorTimeIntervalNoID
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
                              type: integer
                              description: New mmadetector data time_interval ID
          400:
            content:
              application/json:
                schema: Error
        """
        json = self.get_json()

        if 'time_intervals' in json:
            time_intervals = json['time_intervals']
        elif 'time_interval' in json:
            time_intervals = [json['time_interval']]
        else:
            return self.error('time_interval or time_intervals required in json')

        if 'detector_id' not in json:
            return self.error('detector_id required in json')

        with self.Session() as session:
            stmt = MMADetector.select(self.current_user).where(
                MMADetector.id == json['detector_id']
            )
            mmadetector = session.scalars(stmt).first()
            if mmadetector is None:
                return self.error(
                    f'Cannot find mmadetector with ID: {json["detector_id"]}'
                )

            owner_id = self.associated_user_object.id

            # always append the single user group
            single_user_group = self.associated_user_object.single_user_group

            group_ids = json.pop("group_ids", None)
            if group_ids == [] or group_ids is None:
                group_ids = [single_user_group.id]
            elif group_ids == "all":
                group_ids = [g.id for g in self.current_user.accessible_groups]

            if single_user_group.id not in group_ids:
                group_ids.append(single_user_group.id)

            groups = (
                session.scalars(
                    Group.select(self.current_user).where(Group.id.in_(group_ids))
                )
                .unique()
                .all()
            )
            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f'Cannot find one or more groups with IDs: {group_ids}.'
                )

            time_interval_list = []
            for time_interval in time_intervals:
                data = {
                    'time_interval': time_interval,
                    'detector_id': json['detector_id'],
                }

                time_interval = MMADetectorTimeInterval(**data)
                time_interval.mmadetector = mmadetector
                time_interval.groups = groups
                time_interval.owner_id = owner_id
                time_interval_list.append(time_interval)

            session.add_all(time_interval_list)
            session.commit()

            self.push_all(
                action='skyportal/REFRESH_MMASEGMENT',
                payload={'detector_id': time_interval.detector.id},
            )

            self.push_all(
                action='skyportal/REFRESH_MMASEGMENT_SEGMENTS',
                payload={'detector_id': time_interval.detector.id},
            )

            return self.success(
                data={"ids": [time_interval.id for time_interval in time_interval_list]}
            )

    @auth_or_token
    def get(self, time_interval_id=None):
        """
        ---
        single:
          description: Retrieve an mmadetector time_interval
          tags:
            - mmadetector_time_intervals
          parameters:
            - in: path
              name: time_interval_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleMMADetectorTimeInterval
            403:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve multiple time_intervals with given criteria
          tags:
            - mmadetector_time_intervals
          parameters:
            - in: query
              name: observedBefore
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided,
                return only time_interval observed before this time.
            - in: query
              name: observedAfter
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided,
                return only time_interval observed after this time.
            - in: query
              name: detectorIDs
              nullable: true
              type: list
              items:
                type: integer
              description: |
                If provided, filter only time_intervals observed with one of these mmadetector IDs.
            - in: query
              name: groupIDs
              nullable: true
              schema:
                type: list
                items:
                  type: integer
              description: |
                If provided, filter only time_interval saved to one of these group IDs.
        """
        if time_interval_id is not None:
            with self.Session() as session:
                time_interval = session.scalars(
                    MMADetectorTimeInterval.select(session.user_or_token).where(
                        MMADetectorTimeInterval.id == time_interval_id
                    )
                ).first()
                if time_interval is None:
                    return self.error(
                        f'Could not access time_interval {time_interval_id}.',
                        status=403,
                    )
                seg = time_interval.time_interval
                data = {
                    'id': time_interval.id,
                    'time_interval': [seg.lower, seg.upper],
                    'owner': time_interval.owner,
                    'groups': time_interval.groups,
                    'detector': time_interval.detector,
                }
                return self.success(data=data)

        # multiple time_interval
        observed_before = self.get_query_argument('observedBefore', None)
        observed_after = self.get_query_argument('observedAfter', None)
        detector_ids = self.get_query_argument('detectorIDs', None)
        group_ids = self.get_query_argument('groupIDs', None)

        # validate inputs
        try:
            observed_before = (
                arrow.get(observed_before).datetime if observed_before else None
            )
        except (TypeError, ParserError):
            return self.error(f'Cannot parse time input value "{observed_before}".')

        try:
            observed_after = (
                arrow.get(observed_after).datetime if observed_after else None
            )
        except (TypeError, ParserError):
            return self.error(f'Cannot parse time input value "{observed_after}".')

        with self.Session() as session:

            try:
                detector_ids = parse_id_list(detector_ids, MMADetector, session)
                group_ids = parse_id_list(group_ids, Group, session)
            except (ValueError, AccessError) as e:
                return self.error(str(e))

            # filter the time_interval
            time_interval_query = MMADetectorTimeInterval.select(session.user_or_token)
            if detector_ids:
                time_interval_query = time_interval_query.where(
                    MMADetectorTimeInterval.detector_id.in_(detector_ids)
                )

            if group_ids:
                time_interval_query = time_interval_query.where(
                    or_(
                        *[
                            MMADetectorTimeInterval.groups.any(Group.id == gid)
                            for gid in group_ids
                        ]
                    )
                )

            if observed_before:
                time_interval_query = time_interval_query.where(
                    MMADetectorTimeInterval.end_time <= observed_before
                )

            if observed_after:
                time_interval_query = time_interval_query.where(
                    MMADetectorTimeInterval.start_time >= observed_after
                )

            time_intervals = session.scalars(time_interval_query).unique().all()
            data = []
            for time_interval in time_intervals:
                seg = time_interval.time_interval
                data.append(
                    {
                        'id': time_interval.id,
                        'time_interval': [seg.lower, seg.upper],
                        'owner': time_interval.owner,
                        'groups': time_interval.groups,
                        'detector': time_interval.detector,
                    }
                )
            return self.success(data=data)

    @permissions(['Upload data'])
    def patch(self, time_interval_id):
        """
        ---
        description: Update mmadetector time_interval
        tags:
          - mmadetector_time_intervals
        parameters:
          - in: path
            name: time_interval_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: MMADetectorTimeIntervalNoID
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

        try:
            time_interval_id = int(time_interval_id)
        except TypeError:
            return self.error('Could not convert time_interval id to int.')

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        if group_ids == 'all':
            group_ids = [g.id for g in self.current_user.accessible_groups]

        with self.Session() as session:
            stmt = MMADetectorTimeInterval.select(self.current_user).where(
                MMADetectorTimeInterval.id == time_interval_id
            )
            time_interval = session.scalars(stmt).first()

            if group_ids:
                groups = (
                    session.scalars(
                        Group.select(self.current_user).where(Group.id.in_(group_ids))
                    )
                    .unique()
                    .all()
                )
                if {g.id for g in groups} != set(group_ids):
                    return self.error(
                        f'Cannot find one or more groups with IDs: {group_ids}.'
                    )

                if groups:
                    time_interval.groups = time_interval.groups + groups

            if 'time_interval' in data:
                time_interval.time_interval = data['time_interval']

            session.commit()

            self.push_all(
                action='skyportal/REFRESH_MMADETECTOR',
                payload={'detector_id': time_interval.detector.id},
            )

            self.push_all(
                action='skyportal/REFRESH_MMADETECTOR_SEGMENT',
                payload={'detector_id': time_interval.detector.id},
            )

            return self.success()

    @permissions(['Upload data'])
    def delete(self, time_interval_id):
        """
        ---
        description: Delete an mmadetector time_interval
        tags:
          - mmadetector_time_intervals
        parameters:
          - in: path
            name: time_interval_id
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
            time_interval = session.scalars(
                MMADetectorTimeInterval.select(self.current_user, mode="delete").where(
                    MMADetectorTimeInterval.id == time_interval_id
                )
            ).first()
            if time_interval is None:
                return self.error(
                    f'Cannot find time_interval with ID {time_interval_id}'
                )

            detector_id = time_interval.detector.id
            session.delete(time_interval)
            session.commit()

            self.push_all(
                action='skyportal/REFRESH_MMADETECTOR',
                payload={'detector_id': detector_id},
            )

            self.push_all(
                action='skyportal/REFRESH_MMADETECTOR_SEGMENTS',
                payload={'detector_id': detector_id},
            )

            return self.success()
