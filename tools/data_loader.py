#!/usr/bin/env python

import os
import sys
import base64
import textwrap
import time
from os.path import join as pjoin

import requests
import numpy as np
import pandas as pd
import yaml
from yaml import Loader
from regions import Regions
from astropy.table import Table

from baselayer.app.env import load_env, parser

from skyportal.tests import api
from skyportal.tests.patch_requests import patch_requests


patch_requests()


if __name__ == "__main__":
    parser.description = 'Load data into SkyPortal'
    parser.add_argument(
        'data_files', type=str, nargs='+', help='YAML files with data to load'
    )
    parser.add_argument(
        '--host',
        help=textwrap.dedent(
            '''Fully specified URI of the running SkyPortal instance.
                             E.g., https://myserver.com:9000.

                             Defaults to http://localhost on the port specified
                             in the SkyPortal configuration file.'''
        ),
    )
    parser.add_argument(
        '--token',
        help=textwrap.dedent(
            '''Token required for accessing the SkyPortal API.

                             By default, SkyPortal produces a token that is
                             written to .tokens.yaml.  If no token is specified
                             here, that token will be used.'''
        ),
    )
    parser.add_argument(
        '--create_tables',
        action='store_true',
        help="Set to create the SkyPortal database tables before inserting data.",
    )

    env, cfg = load_env()

    # TODO: load multiple files
    if len(env.data_files) > 1:
        raise NotImplementedError("Cannot yet handle multiple data files")

    fname = env.data_files[0]
    src = yaml.load(open(fname), Loader=Loader)
    src_path = os.path.dirname(fname)

    if env.create_tables:
        from baselayer.app.model_util import create_tables
        from skyportal.models import init_db

        RETRIES = 6
        timeout = 3
        for i in range(RETRIES):
            try:
                print(f"Connecting to database {cfg['database']['database']}")
                init_db(**cfg['database'])
            except TimeoutError:
                if i == RETRIES - 1:
                    print('FAIL')
                    print()
                    print(
                        f'Error: Could not connect to SkyPortal database; trying again in {timeout}s'
                    )
                    sys.exit(-1)
                else:
                    time.sleep(timeout)
                    timeout = max(timeout * 2, 30)
                    print('Retrying connection...')

        print("Creating tables")
        create_tables()

    def get_token():
        if env.token:
            return env.token

        try:
            token = yaml.load(open('.tokens.yaml'), Loader=yaml.Loader)['INITIAL_ADMIN']
            return token
        except (FileNotFoundError, TypeError, KeyError):
            return None

    print('Testing connection...', end='')

    RETRIES = 30
    timeout = 3
    admin_token = None
    status = None
    for i in range(RETRIES):
        try:
            previous_admin_token = admin_token
            admin_token = get_token()
            if admin_token != previous_admin_token:
                print('Loaded token from SkyPortal provisioned .tokens.yaml')

            def get(endpoint, token=admin_token):
                response_status, data = api("GET", endpoint, token=token, host=env.host)
                return response_status, data

            def post(endpoint, data, token=admin_token):
                response_status, data = api(
                    "POST", endpoint, data=data, token=token, host=env.host
                )
                return response_status, data

            def assert_post(endpoint, data, token=admin_token):
                response_status, data = post(endpoint, data, token)
                if not response_status == 200 and data["status"] == "success":
                    raise RuntimeError(
                        f'API call to {endpoint} failed with status {status}: {data["message"]}'
                    )
                return data

            if admin_token:
                status, data = get('sysinfo')
            else:
                print('No token specified; reading from ', end='')
                print('SkyPortal generated .tokens.yaml')
                time.sleep(timeout)
                continue

            if status == 200 and data['status'] == 'success':
                break
            else:
                if i == RETRIES - 1:
                    print('FAIL')
                else:
                    time.sleep(timeout)
                    print(f'Expected HTTP 200, received {status}. Trying again.')
                continue
        except requests.exceptions.ConnectionError:
            host = env.host or f'http://localhost:{cfg["ports.app"]}'
            if i == RETRIES - 1:
                print('FAIL')
                print()
                print('Error: Could not connect to SkyPortal instance; please ensure ')
                print(f'       it is running at the given host/port [{host}]')
                sys.exit(-1)
            else:
                time.sleep(timeout)
                print(f'Could not connect to {host}. Trying again.')

    if status not in (200, 400):
        print(f'Fatal: could not connect to server (HTTP status {status})')
        sys.exit(-1)

    if data['status'] != 'success':
        print(
            'Error: Could not authenticate against SkyPortal; please specify a valid token.'
        )
        sys.exit(-1)

    status, response = get('groups/public')
    if status != 200 or response['status'] != 'success':
        print('Error: no public group found; aborting')
        sys.exit(-1)
    public_group_id = response['data']['id']

    error_log = []

    references = {'public_group_id': public_group_id}

    def inject_references(obj):
        if isinstance(obj, dict):
            if 'file' in obj:
                filename = pjoin(src_path, obj['file'])
                if filename.endswith('csv'):
                    df = pd.read_csv(filename).replace({np.nan: None})
                    obj.pop('file')
                    obj.update(df.to_dict(orient='list'))
                elif filename.endswith('.png'):
                    return base64.b64encode(open(filename, 'rb').read())
                elif filename.endswith('xml'):
                    with open(filename, 'rb') as fid:
                        payload = fid.read()
                    return payload
                elif filename.endswith('reg'):
                    return Regions.read(filename).serialize(format='ds9')
                elif filename.endswith('h5') or filename.endswith('hdf5'):
                    try:
                        payload = (
                            Table.read(filename).to_pandas().to_dict(orient='list')
                        )
                    except Exception as e:
                        # sometimes we save HDF5 files using an HDFStore.
                        # in this case we read it as a binary file and return it as "data"
                        if 'values_block_0' in str(e):
                            with open(filename, 'rb') as fid:
                                payload = base64.b64encode(fid.read())
                        else:
                            raise e
                    return payload
                elif filename.endswith('bz2'):
                    payload = (
                        pd.read_csv(filename, compression='bz2')
                        .replace({np.nan: None})
                        .to_dict(orient='list')
                    )
                    return payload
                else:
                    raise NotImplementedError(
                        f'{filename}: Only CSV, PNG, xml, reg, and hdf5 files currently supported for extending individual objects'
                    )

            for k, v in obj.items():
                obj[k] = inject_references(v)
            return obj
        elif isinstance(obj, str) and obj.startswith('='):
            try:
                return references[obj[1:]]
            except KeyError:
                print(
                    f'\nReference {obj[1:]} not found while posting to {endpoint}; skipping'
                )
                raise
        elif isinstance(obj, list):
            return [inject_references(item) for item in obj]
        else:
            return obj

    ENDPOINT_RETRIES = 3

    for endpoint, to_post in src.items():
        # Substitute references in path
        endpoint_parts = endpoint.split('/')
        try:
            for i, part in enumerate(endpoint_parts):
                if part.startswith('='):
                    endpoint_parts[i] = str(references[part[1:]])
        except KeyError:
            print(
                f'\nReference {part[1:]} not found while interpolating endpoint {endpoint}; skipping'
            )
            continue

        endpoint = '/'.join(endpoint_parts)

        print(f'Posting to {endpoint}: ', end='')
        if 'file' in to_post:
            filename = pjoin(src_path, to_post['file'])
            post_objs = yaml.load(open(filename), Loader=yaml.Loader)
        else:
            post_objs = to_post

        for obj in post_objs:
            # Fields that start with =, such as =id, get saved for using as
            # references later on
            saved_fields = {v: k[1:] for k, v in obj.items() if k.startswith('=')}

            # Remove all such fields from the object to be posted
            obj = {k: v for k, v in obj.items() if not k.startswith('=')}

            # Replace all references of the format field: =key or [=key, ..]
            # with the appropriate reference value
            try:
                inject_references(obj)
            except KeyError:
                continue

            if "payload" in obj:
                date_keys = ["start_date", "end_date"]
                for key in date_keys:
                    if key in obj["payload"]:
                        obj["payload"][key] = obj["payload"][key].isoformat()

            ntries = 0
            posted_success = False
            while (ntries < ENDPOINT_RETRIES) and not posted_success:
                status, response = post(endpoint, data=obj)

                print('.' if status == 200 else 'X', end='')
                if status != 200:
                    ntries = ntries + 1
                    continue
                else:
                    posted_success = True

            if status != 200:
                error_log.append(
                    f"/{endpoint}: {response['message'] if response else None}"
                )
            else:
                # Save all references from the response
                for target, field in saved_fields.items():
                    references[target] = response['data'][field]

        print()

    if error_log:
        print("\nError log:")
        print("----------")
        print("\n".join(error_log))

        sys.exit(-1)
