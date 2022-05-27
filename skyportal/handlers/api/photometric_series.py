import uuid
import datetime
import json
from io import StringIO
import base64

from astropy.time import Time
from astropy.table import Table
from marshmallow import INCLUDE, EXCLUDE
from marshmallow.exceptions import ValidationError
import numpy as np
import pandas as pd
import xarray as xr
import sncosmo
from sncosmo.photdata import PhotometricData
import arrow

import sqlalchemy as sa
from sqlalchemy.sql import column, Values
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log
from ..base import BaseHandler
from ...models import (
    AccessError,
    DBSession,
    Annotation,
    Group,
    Stream,
    PhotometricSeries,
    Instrument,
    Obj,
    PHOT_ZP,
    GroupPhotometricSeries,
    StreamPhotometricSeries,
)

from ...enum_types import ALLOWED_MAGSYSTEMS

from .photometry import get_group_ids, get_stream_ids

_, cfg = load_env()


log = make_log('api/photometric_series')


class PhotometricSeriesHandler(BaseHandler):
    def get_groups(self, group_ids):
        groups = []
        if group_ids == "all":
            groups = Group.query.filter(
                Group.name == cfg['misc.public_group_name']
            ).all()
        else:
            groups = Group.get_if_accessible_by(
                group_ids, self.current_user, raise_if_none=True
            )
        return groups

    @permissions(['Upload data'])
    def post(self):
        payload = self.get_json()

        if isinstance(payload['data'], dict):
            payload['data'] = xr.Dataset.from_dict(payload['data'])
        elif isinstance(payload['data'], str):
            try:
                payload['data'] = xr.load_dataset(base64.b64decode(payload['data']))
            except ValueError:
                return self.error(
                    f'Could not decode byte stream as netCDF file.',
                )
        else:
            return self.error(
                'Must provide data field as dictionary or base64 encoded netCDF with an xarray.'
            )

        # ps = PhotometricSeries(ds, payload['series_identifier'], payload['series_obj_id'])

        # must validate some of the required data before loading the schema
        keys = ['obj_id', 'instrument_id', 'filter']
        for k in keys:
            if k not in payload:
                return self.error(f'Missing key: {k}')

        # verify the object exists / is accessible
        try:
            _ = Obj.get_if_accessible_by(
                payload['obj_id'], self.current_user, raise_if_none=True
            )
        except AccessError:
            return self.error(f'Cannot find object with ID= {payload["obj_id"]}')

        instrument = Instrument.query.get(payload['instrument_id'])
        if not instrument:
            return self.error(f'Invalid instrument ID: {payload["instrument_id"]}')

        if payload['filter'] not in instrument.filters:
            return self.error(
                f'Filter {payload["filter"]} not found '
                f'in instrument {instrument.name} (id: {instrument.id}).'
            )

        try:
            group_ids = get_group_ids(payload, self.associated_user_object)
            try:
                groups = self.get_groups(group_ids)
            except AccessError:
                return self.error(
                    f'Invalid group_ids: {group_ids}. Use valid group indices or "all".'
                )
        except ValidationError as e:
            return self.error(e.args[0])

        try:
            stream_ids = get_stream_ids(payload, self.associated_user_object)
            if stream_ids is not None:
                try:
                    streams = Stream.get_if_accessible_by(
                        stream_ids, self.current_user, raise_if_none=True
                    )
                except AccessError:
                    return self.error(f'Cannot find streams with ids: {stream_ids}')
        except ValidationError as e:
            return self.error(e.args[0])

        schema = PhotometricSeries.__schema__(
            exclude=[
                'filename',
                'mjd_first',
                'mjd_mid',
                'mjd_last',
                'mjd_last_detected',
                'is_detected',
                'num_exp',
                'owner_id',
                'hash',
            ]
        )

        validation_errors = schema.validate(payload)
        validation_errors.pop('data')  # cannot exclude data as it is not in the model
        # these can be deduced from the "data" array, and so they can be missing here
        allow_missing_keys = ['exp_time', 'frame_rate']
        for k in allow_missing_keys:
            if k in validation_errors and 'Missing data' in str(validation_errors[k]):
                validation_errors.pop(k)

        if validation_errors:  # return any remaining errors to user
            return self.error(f'Invalid / missing parameters; {validation_errors}')

        # the constructor will fill the data arrays,
        # find frame_rate (and maybe exp_time, ra/dec, etc.)
        # from the data and calculate all the required
        # mjd values, data hash and so on.
        ps = PhotometricSeries(**payload)

        # must manually validate these fields because they could potentially be deduced from "data"
        schema = PhotometricSeries.__schema__(only=allow_missing_keys, unknown=EXCLUDE)
        validation_errors = schema.validate(ps.to_dict())
        if validation_errors:
            return self.error(f'Invalid / missing parameters: {validation_errors}')

        ps.groups = groups
        ps.streams = streams
        ps.owner_id = self.associated_user_object.id

        DBSession().add(ps)

        ps.save_data()  # save the xarray data into file storage

        # Add new stream_photometric_series rows if not already present
        if stream_ids is not None:
            for stream in ps.streams:
                DBSession().add(
                    StreamPhotometricSeries(photometr_id=ps.id, stream_id=stream.id)
                )

        self.verify_and_commit()

        return self.success(data={"id": ps.id})
