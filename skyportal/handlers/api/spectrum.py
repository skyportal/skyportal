import io
from pathlib import Path
from astropy.time import Time
import numpy as np

from sqlalchemy.orm import joinedload

from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.model_util import recursive_to_dict
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    DBSession,
    FollowupRequest,
    Group,
    CommentOnSpectrum,
    Instrument,
    Obj,
    Spectrum,
    User,
    ClassicalAssignment,
)
from ...schema import (
    SpectrumAsciiFilePostJSON,
    SpectrumPost,
    SpectrumAsciiFileParseJSON,
)

_, cfg = load_env()


class SpectrumHandler(BaseHandler):
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

        instrument = Instrument.get_if_accessible_by(
            data['instrument_id'], self.current_user, raise_if_none=True
        )

        # need to do this before the creation of Spectrum because this line flushes.
        owner_id = self.associated_user_object.id

        reducers = []
        for reducer_id in data.pop('reduced_by', []):
            reducer = User.get_if_accessible_by(reducer_id, self.current_user)
            if reducer is None:
                return self.error(f'Invalid reducer ID: {reducer_id}.')
            reducers.append(reducer)

        observers = []
        for observer_id in data.pop('observed_by', []):
            observer = User.get_if_accessible_by(observer_id, self.current_user)
            if observer is None:
                return self.error(f'Invalid observer ID: {observer_id}.')
            observers.append(observer)

        spec = Spectrum(**data)
        spec.observers = observers
        spec.reducers = reducers
        spec.instrument = instrument
        spec.groups = groups
        spec.owner_id = owner_id
        DBSession().add(spec)
        self.verify_and_commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': spec.obj.internal_key},
        )

        self.push_all(
            action='skyportal/REFRESH_SOURCE_SPECTRA',
            payload={'obj_key': spec.obj.internal_key},
        )

        return self.success(data={"id": spec.id})

    @auth_or_token
    def get(self, spectrum_id):
        """
        ---
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
          400:
            content:
              application/json:
                schema: Error
        """

        spectrum = Spectrum.get_if_accessible_by(
            spectrum_id,
            self.current_user,
            raise_if_none=True,
        )
        comments = (
            CommentOnSpectrum.query_records_accessible_by(
                self.current_user,
                options=[joinedload(CommentOnSpectrum.groups)],
            )
            .filter(CommentOnSpectrum.spectrum_id == spectrum_id)
            .all()
        )

        spec_dict = recursive_to_dict(spectrum)
        spec_dict["instrument_name"] = spectrum.instrument.name
        spec_dict["groups"] = spectrum.groups
        spec_dict["reducers"] = spectrum.reducers
        spec_dict["observers"] = spectrum.observers
        spec_dict["owner"] = spectrum.owner
        spec_dict["comments"] = comments
        self.verify_and_commit()
        return self.success(data=spec_dict)

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

        for k in data:
            setattr(spectrum, k, data[k])

        self.verify_and_commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': spectrum.obj.internal_key},
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
            payload={'obj_id': spectrum.obj_id},
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
        for reducer_id in json.get('reduced_by', []):
            reducer = User.get_if_accessible_by(reducer_id, self.current_user)
            if reducer is None:
                raise ValidationError(f'Invalid reducer ID: {reducer_id}.')
            reducers.append(reducer)

        observers = []
        for observer_id in json.get('observed_by', []):
            observer = User.get_if_accessible_by(observer_id, self.current_user)
            if observer is None:
                raise ValidationError(f'Invalid observer ID: {observer_id}.')
            observers.append(observer)

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
        spec.reducers = reducers
        spec.observers = observers

        DBSession().add(spec)
        self.verify_and_commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': spec.obj.internal_key},
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
                    options=[joinedload(CommentOnSpectrum.groups)],
                )
                .filter(CommentOnSpectrum.spectrum_id == spec.id)
                .all()
            )

            spec_dict["comments"] = sorted(
                [
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
                ],
                key=lambda x: x["created_at"],
                reverse=True,
            )
            spec_dict["instrument_name"] = spec.instrument.name
            spec_dict["groups"] = spec.groups
            spec_dict["reducers"] = spec.reducers
            spec_dict["observers"] = spec.observers
            spec_dict["owner"] = spec.owner

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
