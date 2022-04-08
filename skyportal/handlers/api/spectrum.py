import io
from pathlib import Path
from astropy.time import Time
import arrow
from arrow import ParserError
import numpy as np
import pandas as pd
import sncosmo
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, Column

from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.model_util import recursive_to_dict
from baselayer.app.env import load_env
from baselayer.log import make_log
from baselayer.app.custom_exceptions import AccessError

from .photometry import add_external_photometry
from ..base import BaseHandler
from ...models import (
    DBSession,
    FollowupRequest,
    Group,
    CommentOnSpectrum,
    AnnotationOnSpectrum,
    Instrument,
    Obj,
    Spectrum,
    SpectrumReducer,
    SpectrumObserver,
    User,
    ClassicalAssignment,
)
from ...models.schema import (
    SpectrumAsciiFilePostJSON,
    SpectrumPost,
    SpectrumAsciiFileParseJSON,
)

from ...enum_types import ALLOWED_SPECTRUM_TYPES, default_spectrum_type

_, cfg = load_env()
log = make_log('api/spectrum')


class SpectrumHandler(BaseHandler):
    def get_groups(self, group_ids):
        groups = []
        if group_ids is None:
            groups = None
        elif group_ids == "all":
            groups = Group.query.filter(
                Group.name == cfg['misc.public_group_name']
            ).all()
        else:
            groups = Group.get_if_accessible_by(
                group_ids, self.current_user, raise_if_none=True
            )
        return groups

    def parse_id_list(self, id_list, model_class):
        """
        Return a list of integer IDs from the comma separated
        string of IDs given by the query argument, and the
        model/table to be queried.

        Parameters
        ----------
        id_list: string
            Comma separated list of integer values.
        model_class: class
            A skyportal data model class, e.g., Group, Instrument.
        """

        if id_list is None:
            return  # silently pass through any None values

        try:
            accessible_rows = model_class.get_records_accessible_by(self.current_user)
            validated_ids = []
            for id in id_list.split(','):
                id = int(id)
                if id not in [row.id for row in accessible_rows]:
                    raise AccessError(
                        f'Invalid {model_class.__name__} IDs field ("{id_list}"); '
                        f'Not all {model_class.__name__} IDs are valid/accessible'
                    )
                validated_ids.append(id)
        except ValueError:
            raise ValueError(
                f'Invalid {model_class.__name__} IDs field ("{id_list}"); '
                f'Could not parse all elements to integers'
            )

        return validated_ids

    @staticmethod
    def parse_string_list(str_list):
        """
        Parse a string that is either a single value,
        or a comma separated list of values.
        Returns a list of strings in either case.
        If input is an empty string returns an
        empty list.
        """
        if isinstance(str_list, str):
            if len(str_list) == 0:
                return []
            elif "," in str_list:
                return [c.strip() for c in str_list.split(",")]
            else:
                return [str_list.strip()]
        else:
            raise TypeError('Must input a string!')

    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload spectrum
        tags:
          - spectra
        requestBody:
          content:
            application/json:
              schema: SpectrumPost
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
                              description: New spectrum ID
          400:
            content:
              application/json:
                schema: Error
        """
        json = self.get_json()

        try:
            data = SpectrumPost.load(json)
        except ValidationError as e:
            return self.error(
                f'Invalid / missing parameters; {e.normalized_messages()}'
            )

        # always append the single user group
        single_user_group = self.associated_user_object.single_user_group

        group_ids = data.pop("group_ids", None)
        if group_ids == [] or group_ids is None:
            groups = [single_user_group]
        else:
            groups = self.get_groups(group_ids)

        if single_user_group not in groups:
            groups.append(single_user_group)

        instrument = Instrument.get_if_accessible_by(
            data['instrument_id'], self.current_user, raise_if_none=True
        )

        # need to do this before the creation of Spectrum because this line flushes.
        owner_id = self.associated_user_object.id

        reducers = []
        external_reducer = data.pop("external_reducer", None)
        for reducer_id in data.pop('reduced_by', []):
            reducer = User.get_if_accessible_by(reducer_id, self.current_user)
            if reducer is None:
                return self.error(f'Invalid reducer ID: {reducer_id}.')
            reducer_association = SpectrumReducer(external_reducer=external_reducer)
            reducer_association.user = reducer
            reducers.append(reducer_association)

        if len(reducers) == 0 and external_reducer is not None:
            self.error(
                "At least one valid user must be provided as a reducer point of contact via the 'reduced_by' parameter."
            )

        observers = []
        external_observer = data.pop("external_observer", None)
        for observer_id in data.pop('observed_by', []):
            observer = User.get_if_accessible_by(observer_id, self.current_user)
            if observer is None:
                return self.error(f'Invalid observer ID: {observer_id}.')
            observer_association = SpectrumObserver(external_observer=external_observer)
            observer_association.user = observer
            observers.append(observer_association)

        if len(observers) == 0 and external_observer is not None:
            self.error(
                "At least one valid user must be provided as an "
                "observer point of contact via the 'observed_by' parameter."
            )

        if "units" in data:
            if not data["units"] in ["Jy", "AB", "erg/s/cm/cm/AA"]:
                return self.error("units must be Jy, AB, or erg/s/cm/cm/AA")

        spec = Spectrum(**data)
        spec.instrument = instrument

        spec.groups = groups
        spec.owner_id = owner_id
        if spec.type is None:
            spec.type = default_spectrum_type
        DBSession().add(spec)
        for reducer in reducers:
            reducer.spectrum = spec
            DBSession().add(reducer)
        for observer in observers:
            observer.spectrum = spec
            DBSession().add(observer)
        self.verify_and_commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': spec.obj.internal_key},
        )

        self.push_all(
            action='skyportal/REFRESH_SOURCE_SPECTRA',
            payload={'obj_internal_key': spec.obj.internal_key},
        )

        return self.success(data={"id": spec.id})

    @auth_or_token
    def get(self, spectrum_id=None):
        """
        ---
        single:
          description: Retrieve a spectrum
          tags:
            - spectra
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
                  schema: SingleSpectrum
            403:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve multiple spectra with given criteria
          tags:
            - spectra
          parameters:
            - in: query
              name: minimalPayload
              nullable: true
              default: false
              schema:
                type: boolean
              description: |
                If true, return only the minimal metadata
                about each spectrum, instead of returning
                the potentially large payload that includes
                wavelength/flux and also comments and annotations.
                The metadata that is always included is:
                id, obj_id, owner_id, origin, type, label,
                observed_at, created_at, modified,
                instrument_id, instrument_name, original_file_name,
                followup_request_id, assignment_id, and altdata.
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
              name: objID
              nullable: true
              schema:
                type: string
              description: |
                Return any spectra on an object with ID that has a (partial) match
                to this argument (i.e., the given argument is "in" the object's ID).
            - in: query
              name: instrumentIDs
              nullable: true
              type: list
              items:
                type: integer
              description: |
                If provided, filter only spectra observed with one of these instrument IDs.
            - in: query
              name: groupIDs
              nullable: true
              schema:
                type: list
                items:
                  type: integer
              description: |
                If provided, filter only spectra saved to one of these group IDs.
            - in: query
              name: followupRequestIDs
              nullable: true
              schema:
                type: list
                items:
                  type: integer
              description: |
                If provided, filter only spectra associate with these
                followup request IDs.
            - in: query
              name: assignmentIDs
              nullable: true
              schema:
                type: list
                items:
                  type: integer
              description: |
                If provided, filter only spectra associate with these
                assignment request IDs.
            - in: query
              name: origin
              nullable: true
              schema:
                type: string
              description: |
                Return any spectra that have an origin with a (partial) match
                to any of the values in this comma separated list.
            - in: query
              name: label
              nullable: true
              schema:
                type: string
              description: |
                Return any spectra that have an origin with a (partial) match
                to any of the values in this comma separated list.
            - in: query
              name: type
              nullable: true
              schema:
                type: string
              description: |
                Return spectra of the given type or types
                (match multiple values using a comma separated list).
                Types of spectra are defined in the config,
                e.g., source, host or host_center.
            - in: query
              name: commentsFilter
              nullable: true
              schema:
                type: array
                items:
                  type: string
              explode: false
              style: simple
              description: |
                Comma-separated string of comment text to filter for spectra matching.
            - in: query
              name: commentsFilterAuthor
              nullable: true
              schema:
                type: string
              description: |
                Comma separated string of authors.
                Only comments from these authors are used
                when filtering with the commentsFilter.
            - in: query
              name: commentsFilterBefore
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided,
                only return sources that have comments before this time.
            - in: query
              name: commentsFilterAfter
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided,
                only return sources that have comments after this time.
        """

        if spectrum_id is not None:
            try:
                spectrum = Spectrum.get_if_accessible_by(
                    spectrum_id,
                    self.current_user,
                    raise_if_none=True,
                )
            except AccessError:
                return self.error(
                    f'Could not access spectrum {spectrum_id}.', status=403
                )
            comments = (
                CommentOnSpectrum.query_records_accessible_by(
                    self.current_user,
                    options=[joinedload(CommentOnSpectrum.groups)],
                )
                .filter(CommentOnSpectrum.spectrum_id == spectrum_id)
                .all()
            )
            annotations = (
                AnnotationOnSpectrum.query_records_accessible_by(self.current_user)
                .filter(AnnotationOnSpectrum.spectrum_id == spectrum_id)
                .all()
            )

            spec_dict = recursive_to_dict(spectrum)
            spec_dict["instrument_name"] = spectrum.instrument.name
            spec_dict["groups"] = spectrum.groups
            spec_dict["reducers"] = spectrum.reducers
            spec_dict["observers"] = spectrum.observers
            spec_dict["owner"] = spectrum.owner
            spec_dict["comments"] = comments
            spec_dict["annotations"] = annotations

            external_reducer = (
                DBSession()
                .query(SpectrumReducer.external_reducer)
                .filter(SpectrumReducer.spectr_id == spectrum_id)
                .first()
            )
            if external_reducer is not None:
                spec_dict["external_reducer"] = external_reducer[0]

            external_observer = (
                DBSession()
                .query(SpectrumObserver.external_observer)
                .filter(SpectrumObserver.spectr_id == spectrum_id)
                .first()
            )
            if external_observer is not None:
                spec_dict["external_observer"] = external_observer[0]

            self.verify_and_commit()
            return self.success(data=spec_dict)

        # multiple spectra
        minimal_payload = self.get_query_argument('minimalPayload', False)
        observed_before = self.get_query_argument('observedBefore', None)
        observed_after = self.get_query_argument('observedAfter', None)
        obj_id = self.get_query_argument('objID', None)
        instrument_ids = self.get_query_argument('instrumentIDs', None)
        group_ids = self.get_query_argument('groupIDs', None)
        followup_ids = self.get_query_argument('followupRequestIDs', None)
        assignment_ids = self.get_query_argument('assignmentIDs', None)
        spec_origin = self.get_query_argument('origin', None)
        spec_label = self.get_query_argument('label', None)
        spec_type = self.get_query_argument('type', None)
        comments_filter = self.get_query_argument('commentsFilter', None)
        comments_filter_author = self.get_query_argument('commentsFilterAuthor', None)
        comments_filter_before = self.get_query_argument('commentsFilterBefore', None)
        comments_filter_after = self.get_query_argument('commentsFilterAfter', None)

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

        try:
            instrument_ids = self.parse_id_list(instrument_ids, Instrument)
            group_ids = self.parse_id_list(group_ids, Group)
            followup_ids = self.parse_id_list(followup_ids, FollowupRequest)
            assignment_ids = self.parse_id_list(assignment_ids, ClassicalAssignment)
        except (ValueError, AccessError) as e:
            return self.error(str(e))

        if obj_id is not None:
            try:
                Obj.get_if_accessible_by(obj_id, self.current_user)
            except AccessError:
                return self.error(f'Cannot find object with ID "{obj_id}"')

        if spec_origin is not None:
            try:
                spec_origin = self.parse_string_list(spec_origin)
            except TypeError:
                return self.error(f'Cannot parse "origin" argument "{spec_origin}".')

        if spec_label is not None:
            try:
                spec_label = self.parse_string_list(spec_label)
            except TypeError:
                return self.error(f'Cannot parse "label" argument "{spec_label}".')

        if spec_type is not None:
            try:
                spec_type = self.parse_string_list(spec_type)
            except TypeError:
                return self.error(f'Cannot parse "type" argument "{spec_type}".')
            for t in spec_type:
                if t not in ALLOWED_SPECTRUM_TYPES:
                    return self.error(
                        f'Spectrum type "{t}" is not in list of allowed '
                        f'spectrum types: {ALLOWED_SPECTRUM_TYPES}.'
                    )

        if comments_filter is not None:
            try:
                comments_filter = self.parse_string_list(comments_filter)
            except TypeError:
                return self.error(
                    f'Cannot parse "commentsFilter" argument "{comments_filter}".'
                )

        if comments_filter_author is not None:
            try:
                comments_filter_author = self.parse_string_list(comments_filter_author)
            except TypeError:
                return self.error(
                    f'Cannot parse "commentsFilterAuthor" argument "{comments_filter_author}".'
                )

        if comments_filter_before is not None:
            try:
                comments_filter_before = arrow.get(comments_filter_before).datetime
            except (TypeError, ParserError):
                return self.error(
                    f'Cannot parse time input value "{comments_filter_before}".'
                )

        if comments_filter_after is not None:
            try:
                comments_filter_after = arrow.get(comments_filter_after).datetime
            except (TypeError, ParserError):
                return self.error(
                    f'Cannot parse time input value "{comments_filter_after}".'
                )

        # filter the spectra
        if minimal_payload:
            columns = [
                'id',
                'owner_id',
                'obj_id',
                'observed_at',
                'origin',
                'type',
                'label',
                'instrument_id',
                'followup_request_id',
                'assignment_id',
                'altdata',
                'original_file_filename',
            ]
            columns = [Column(c) for c in columns]

            spec_query = Spectrum.query_records_accessible_by(
                self.current_user,
                columns=columns,
            )
        else:
            spec_query = Spectrum.query_records_accessible_by(
                self.current_user,
            )

        if instrument_ids:
            spec_query = spec_query.filter(Spectrum.instrument_id.in_(instrument_ids))

        if group_ids:
            spec_query = spec_query.filter(
                or_(*[Spectrum.groups.any(Group.id == gid) for gid in group_ids])
            )

        if followup_ids:
            spec_query = spec_query.filter(
                Spectrum.followup_request_id.in_(followup_ids)
            )

        if assignment_ids:
            spec_query = spec_query.filter(Spectrum.assignment_id.in_(assignment_ids))

        if obj_id:
            spec_query = spec_query.filter(Spectrum.obj_id.contains(obj_id.strip()))

        if observed_before:
            spec_query = spec_query.filter(Spectrum.observed_at <= observed_before)

        if observed_after:
            spec_query = spec_query.filter(Spectrum.observed_at >= observed_after)

        if spec_origin:
            spec_query = spec_query.filter(
                or_(*[Spectrum.origin.contains(value) for value in spec_origin])
            )

        if spec_label:
            spec_query = spec_query.filter(
                or_(*[Spectrum.label.contains(value) for value in spec_label])
            )

        if spec_type:
            spec_query = spec_query.filter(Spectrum.type.in_(spec_type))

        spectra = spec_query.all()

        result_spectra = recursive_to_dict(spectra)

        if (
            not minimal_payload
            or (comments_filter is not None)
            or (comments_filter_author is not None)
            or (comments_filter_before is not None)
            or (comments_filter_after is not None)
        ):
            new_result_spectra = []
            for spec_dict in result_spectra:
                comments_query = CommentOnSpectrum.query_records_accessible_by(
                    self.current_user,
                    options=[joinedload(CommentOnSpectrum.groups)],
                ).filter(CommentOnSpectrum.spectrum_id == spec_dict['id'])

                if not minimal_payload:  # grab these before further filtering
                    spec_dict['comments'] = recursive_to_dict(comments_query.all())

                if (
                    (comments_filter is not None)
                    or (comments_filter_author is not None)
                    or (comments_filter_before is not None)
                    or (comments_filter_after is not None)
                ):
                    if comments_filter_before:
                        comments_query = comments_query.filter(
                            CommentOnSpectrum.created_at <= comments_filter_before
                        )
                    if comments_filter_after:
                        comments_query = comments_query.filter(
                            CommentOnSpectrum.created_at >= comments_filter_after
                        )

                    comments = comments_query.all()
                    if not comments:  # if nothing passed, this spectrum is rejected
                        continue

                    # check the author and free text also match at least one comment
                    author_check = np.zeros(len(comments), dtype=bool)
                    text_check = np.zeros(len(comments), dtype=bool)

                    for i, com in enumerate(comments):
                        if comments_filter_author is None or any(
                            [cf in com.author.username for cf in comments_filter_author]
                        ):
                            author_check[i] = True
                        if comments_filter is None or any(
                            [cf in com.text for cf in comments_filter]
                        ):
                            text_check[i] = True

                    # none of the comments have both author and free text match
                    if not np.any(author_check & text_check):
                        continue

                new_result_spectra.append(
                    spec_dict
                )  # only append what passed all the cuts

            result_spectra = new_result_spectra

        if not minimal_payload:  # add other data to each spectrum
            for (spec, spec_dict) in zip(spectra, result_spectra):
                annotations = (
                    AnnotationOnSpectrum.query_records_accessible_by(self.current_user)
                    .filter(AnnotationOnSpectrum.spectrum_id == spec.id)
                    .all()
                )
                spec_dict['annotations'] = recursive_to_dict(annotations)
                external_reducer = (
                    DBSession()
                    .query(SpectrumReducer.external_reducer)
                    .filter(SpectrumReducer.spectr_id == spec.id)
                    .first()
                )
                if external_reducer is not None:
                    spec_dict['external_reducer'] = recursive_to_dict(
                        external_reducer[0]
                    )

                spec_dict['reducers'] = recursive_to_dict(spec.reducers)

                external_observer = (
                    DBSession()
                    .query(SpectrumObserver.external_observer)
                    .filter(SpectrumObserver.spectr_id == spec.id)
                    .first()
                )
                if external_observer is not None:
                    spec_dict['external_observer'] = recursive_to_dict(
                        external_observer[0]
                    )

                spec_dict['observers'] = recursive_to_dict(spec.observers)

                spec_dict['instrument_name'] = spec.instrument.name

                spec_dict['groups'] = recursive_to_dict(spec.groups)
                spec_dict['owner'] = recursive_to_dict(spec.owner)

        result_spectra = sorted(result_spectra, key=lambda x: x['observed_at'])

        self.verify_and_commit()
        return self.success(data=result_spectra)

    @permissions(['Upload data'])
    def put(self, spectrum_id):
        """
        ---
        description: Update spectrum
        tags:
          - spectra
        parameters:
          - in: path
            name: spectrum_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: SpectrumPost
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

        spectrum = Spectrum.get_if_accessible_by(
            spectrum_id, self.current_user, mode="update", raise_if_none=True
        )

        data = self.get_json()

        try:
            data = SpectrumPost.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )

        group_ids = data.pop("group_ids", None)
        groups = self.get_groups(group_ids)

        if groups:
            spectrum.groups = spectrum.groups + groups
        for k in data:
            setattr(spectrum, k, data[k])

        self.verify_and_commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': spectrum.obj.internal_key},
        )
        self.push_all(
            action='skyportal/REFRESH_SOURCE_SPECTRA',
            payload={'obj_internal_key': spectrum.obj.internal_key},
        )
        return self.success()

    @permissions(['Upload data'])
    def delete(self, spectrum_id):
        """
        ---
        description: Delete a spectrum
        tags:
          - spectra
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
        spectrum = Spectrum.get_if_accessible_by(
            spectrum_id, self.current_user, mode="delete", raise_if_none=True
        )
        obj_key = spectrum.obj.internal_key
        DBSession().delete(spectrum)
        self.verify_and_commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': obj_key},
        )

        self.push_all(
            action='skyportal/REFRESH_SOURCE_SPECTRA',
            payload={'obj_internal_key': spectrum.obj.internal_key},
        )

        return self.success()


class ASCIIHandler:
    def spec_from_ascii_request(
        self, validator=SpectrumAsciiFilePostJSON, return_json=False
    ):
        """Helper method to read in Spectrum objects from ASCII POST."""
        json = self.get_json()

        try:
            json = validator.load(json)
        except ValidationError as e:
            raise ValidationError(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )

        ascii = json.pop('ascii')

        # maximum size 10MB - above this don't parse. Assuming ~1 byte / char
        if len(ascii) > 1e7:
            raise ValueError('File must be smaller than 10MB.')

        # pass ascii in as a file-like object
        try:
            file = io.BytesIO(ascii.encode('ascii'))
        except UnicodeEncodeError:
            raise ValueError(
                'Unable to parse uploaded spectrum file as ascii. '
                'Ensure the file is not a FITS file and retry.'
            )

        spec = Spectrum.from_ascii(
            file,
            obj_id=json.get('obj_id', None),
            instrument_id=json.get('instrument_id', None),
            type=json.get('type', None),
            label=json.get('label', None),
            observed_at=json.get('observed_at', None),
            wave_column=json.get('wave_column', None),
            flux_column=json.get('flux_column', None),
            fluxerr_column=json.get('fluxerr_column', None),
        )
        spec.original_file_string = ascii
        spec.owner = self.associated_user_object
        if return_json:
            return spec, json
        return spec


class SpectrumASCIIFileHandler(BaseHandler, ASCIIHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload spectrum from ASCII file
        tags:
          - spectra
        requestBody:
          content:
            application/json:
              schema: SpectrumAsciiFilePostJSON
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
                              description: New spectrum ID
          400:
            content:
              application/json:
                schema: Error
        """

        try:
            spec, json = self.spec_from_ascii_request(return_json=True)
        except Exception as e:
            return self.error(f'Error parsing spectrum: {e.args[0]}')

        filename = json.pop('filename')

        Obj.get_if_accessible_by(json['obj_id'], self.current_user, raise_if_none=True)

        Instrument.get_if_accessible_by(
            json['instrument_id'], self.current_user, raise_if_none=True
        )

        # always add the single user group
        single_user_group = self.associated_user_object.single_user_group

        group_ids = json.pop('group_ids', [])
        if group_ids is None:
            groups = [single_user_group]
        else:
            if group_ids == "all":
                groups = Group.query.filter(
                    Group.name == cfg['misc.public_group_name']
                ).all()
            else:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )

        if single_user_group not in groups:
            groups.append(single_user_group)

        reducers = []
        external_reducer = json.pop("external_reducer", None)
        for reducer_id in json.pop('reduced_by', []):
            reducer = User.get_if_accessible_by(reducer_id, self.current_user)
            if reducer is None:
                return self.error(f'Invalid reducer ID: {reducer_id}.')
            reducer_association = SpectrumReducer(external_reducer=external_reducer)
            reducer_association.user = reducer
            reducers.append(reducer_association)
        if len(reducers) == 0 and external_reducer is not None:
            self.error(
                "At least one valid user must be provided as a reducer point of contact via the 'reduced_by' parameter."
            )

        observers = []
        external_observer = json.pop("external_observer", None)
        for observer_id in json.pop('observed_by', []):
            observer = User.get_if_accessible_by(observer_id, self.current_user)
            if observer is None:
                return self.error(f'Invalid observer ID: {observer_id}.')
            observer_association = SpectrumObserver(external_observer=external_observer)
            observer_association.user = observer
            observers.append(observer_association)
        if len(observers) == 0 and external_observer is not None:
            self.error(
                "At least one valid user must be provided as an observer point of contact via the 'observed_by' parameter."
            )

        # will never KeyError as missing value is imputed
        followup_request_id = json.pop('followup_request_id', None)
        if followup_request_id is not None:
            followup_request = FollowupRequest.get_if_accessible_by(
                followup_request_id, self.current_user, raise_if_none=True
            )
            spec.followup_request = followup_request
            for group in followup_request.target_groups:
                if group not in groups:
                    groups.append(group)

        assignment_id = json.pop('assignment_id', None)
        if assignment_id is not None:
            assignment = ClassicalAssignment.get_if_accessible_by(
                assignment_id, self.current_user, raise_if_none=True
            )
            if assignment is None:
                return self.error('Invalid assignment.')
            spec.assignment = assignment
            if assignment.run.group is not None:
                groups.append(assignment.run.group)

        spec.original_file_filename = Path(filename).name
        spec.groups = groups

        DBSession().add(spec)
        for reducer in reducers:
            reducer.spectrum = spec
            DBSession().add(reducer)
        for observer in observers:
            observer.spectrum = spec
            DBSession().add(observer)

        self.verify_and_commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': spec.obj.internal_key},
        )

        self.push_all(
            action='skyportal/REFRESH_SOURCE_SPECTRA',
            payload={'obj_internal_key': spec.obj.internal_key},
        )

        return self.success(data={'id': spec.id})


class SpectrumASCIIFileParser(BaseHandler, ASCIIHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Parse spectrum from ASCII file
        tags:
          - spectra
        requestBody:
          content:
            application/json:
              schema: SpectrumAsciiFileParseJSON
        responses:
          200:
            content:
              application/json:
                schema: SpectrumNoID
          400:
            content:
              application/json:
                schema: Error
        """

        try:
            spec = self.spec_from_ascii_request(validator=SpectrumAsciiFileParseJSON)
        except Exception as e:
            return self.error(f'Error parsing spectrum: {e.args[0]}')
        return self.success(data=spec)


class ObjSpectraHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        """
        ---
        description: Retrieve all spectra associated with an Object
        tags:
          - spectra
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: ID of the object to retrieve spectra for
          - in: query
            name: normalization
            required: false
            schema:
              type: string
            description: |
              what normalization is needed for the spectra (e.g., "median").
              If omitted, returns the original spectrum.
              Options for normalization are:
              - median: normalize the flux to have median==1

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
                            obj_id:
                              type: string
                              description: The ID of the requested Obj
                            spectra:
                              type: array
                              items:
                                $ref: '#/components/schemas/Spectrum'
          400:
            content:
              application/json:
                schema: Error
        """

        obj = Obj.get_if_accessible_by(obj_id, self.current_user)
        if obj is None:
            return self.error('Invalid object ID.')

        spectra = (
            Spectrum.query_records_accessible_by(self.current_user)
            .filter(Spectrum.obj_id == obj_id)
            .all()
        )

        return_values = []
        for spec in spectra:
            spec_dict = recursive_to_dict(spec)
            comments = (
                CommentOnSpectrum.query_records_accessible_by(
                    self.current_user,
                )
                .filter(CommentOnSpectrum.spectrum_id == spec.id)
                .all()
            )
            annotations = (
                AnnotationOnSpectrum.query_records_accessible_by(self.current_user)
                .filter(AnnotationOnSpectrum.spectrum_id == spec.id)
                .all()
            )

            spec_dict["comments"] = sorted(
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
                    }
                    for c in comments
                ),
                key=lambda x: x["created_at"],
                reverse=True,
            )
            annotations = [
                {**a.to_dict(), 'author': a.author.to_dict()} for a in annotations
            ]
            spec_dict["annotations"] = annotations
            spec_dict["instrument_name"] = spec.instrument.name
            spec_dict["groups"] = spec.groups
            spec_dict["reducers"] = spec.reducers
            spec_dict["observers"] = spec.observers
            external_reducer = (
                DBSession()
                .query(SpectrumReducer.external_reducer)
                .filter(SpectrumReducer.spectr_id == spec.id)
                .first()
            )
            if external_reducer is not None:
                spec_dict["external_reducer"] = external_reducer[0]
            external_observer = (
                DBSession()
                .query(SpectrumObserver.external_observer)
                .filter(SpectrumObserver.spectr_id == spec.id)
                .first()
            )
            if external_observer is not None:
                spec_dict["external_observer"] = external_observer[0]
            spec_dict["owner"] = spec.owner
            spec_dict["obj_internal_key"] = obj.internal_key

            return_values.append(spec_dict)

        normalization = self.get_query_argument('normalization', None)

        if normalization is not None:
            if normalization == "median":
                for s in return_values:
                    norm = np.median(np.abs(s["fluxes"]))
                    norm = norm if norm != 0.0 else 1e-20
                    if not (np.isfinite(norm) and norm > 0):
                        # otherwise normalize the value at the median wavelength to 1
                        median_wave_index = np.argmin(
                            np.abs(s["wavelengths"] - np.median(s["wavelengths"]))
                        )
                        norm = s["fluxes"][median_wave_index]

                    s["fluxes"] = s["fluxes"] / norm
            else:
                return self.error(
                    f'Invalid "normalization" value "{normalization}, use '
                    '"median" or None'
                )
        self.verify_and_commit()
        return self.success(data={'obj_id': obj.id, 'spectra': return_values})


class SpectrumRangeHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve spectra for given instrument within date range
        tags:
          - spectra
        parameters:
          - in: query
            name: instrument_ids
            required: false
            schema:
              type: list of integers
            description: |
              Instrument id numbers of spectrum.  If None, retrieve
              for all instruments.
          - in: query
            name: min_date
            required: false
            schema:
              type: ISO UTC date string
            description: |
              Minimum UTC date of range in ISOT format.  If None,
              open ended range.
          - in: query
            name: max_date
            required: false
            schema:
              type: ISO UTC date string
            description: |
              Maximum UTC date of range in ISOT format. If None,
              open ended range.

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
                            obj_id:
                              type: string
                              description: The ID of the requested Obj
                            spectra:
                              type: array
                              items:
                                $ref: '#/components/schemas/Spectrum'
          400:
            content:
              application/json:
                schema: Error
        """

        instrument_ids = self.get_query_arguments('instrument_ids')
        min_date = self.get_query_argument('min_date', None)
        max_date = self.get_query_argument('max_date', None)

        if len(instrument_ids) > 0:
            query = Spectrum.query_records_accessible_by(self.current_user).filter(
                Spectrum.instrument_id.in_(instrument_ids)
            )
        else:
            query = Spectrum.query_records_accessible_by(self.current_user)

        if min_date is not None:
            utc = Time(min_date, format='isot', scale='utc')
            query = query.filter(Spectrum.observed_at >= utc.isot)
        if max_date is not None:
            utc = Time(max_date, format='isot', scale='utc')
            query = query.filter(Spectrum.observed_at <= utc.isot)

        self.verify_and_commit()
        return self.success(data=query.all())


class SyntheticPhotometryHandler(BaseHandler):
    @auth_or_token
    def post(self, spectrum_id):
        """
        ---
        description: Create synthetic photometry from a spectrum
        tags:
          - spectra
        parameters:
          - in: path
            name: spectrum_id
            required: true
            schema:
              type: integer
          - in: query
            name: filters
            schema:
              type: list
            required: true
            description: |
                List of filters
        responses:
          200:
            content:
              application/json:
                schema: SingleSpectrum
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()
        filters = data.get('filters')

        spectrum = Spectrum.get_if_accessible_by(
            spectrum_id,
            self.current_user,
            raise_if_none=False,
        )
        if spectrum is None:
            return self.error(f'No spectrum with id {spectrum_id}')

        spec_dict = recursive_to_dict(spectrum)
        wav = spec_dict['wavelengths']
        flux = spec_dict['fluxes']
        err = spec_dict['errors']
        obstime = spec_dict['observed_at']

        try:
            spec = sncosmo.Spectrum(
                wav, flux * spectrum.astropy_units, err * spectrum.astropy_units
            )
        except TypeError:
            spec = sncosmo.Spectrum(wav, flux * spectrum.astropy_units)

        data_list = []
        for filt in filters:
            try:
                mag = spec.bandmag(filt, magsys='ab')
                magerr = 0
            except ValueError as e:
                return self.error(
                    f"Unable to generate synthetic photometry for filter {filt}: {e}"
                )

            data_list.append(
                {
                    'mjd': Time(obstime, format='datetime').mjd,
                    'ra': spectrum.obj.ra,
                    'dec': spectrum.obj.dec,
                    'mag': mag,
                    'magerr': magerr,
                    'filter': filt,
                    'limiting_mag': 25.0,
                }
            )

        if len(data_list) > 0:
            df = pd.DataFrame.from_dict(data_list)
            df['magsys'] = 'ab'
            data_out = {
                'obj_id': spectrum.obj.id,
                'instrument_id': spectrum.instrument.id,
                'group_ids': [g.id for g in self.current_user.accessible_groups],
                **df.to_dict(orient='list'),
            }
            add_external_photometry(data_out, self.associated_user_object)

            return self.success()
        return self.success()
