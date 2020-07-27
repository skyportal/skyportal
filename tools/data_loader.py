#!/usr/bin/env python

import os
import sys
import base64
from pathlib import Path
import textwrap
from contextlib import contextmanager

import requests
import pandas as pd
import yaml
from yaml import Loader
import tdtax

from baselayer.app.env import load_env, parser
from baselayer.app.model_util import status
from skyportal.tests import api


@contextmanager
def status(message):
    print(f'[·] {message}', end='')
    try:
        yield
    except Exception as e:
        print(f'\r[✗] {message}: {repr(e)}')
    else:
        print(f'\r[✓] {message}')


if __name__ == "__main__":
    parser.description = 'Load data into SkyPortal'
    parser.add_argument('data_files', type=str, nargs='+',
                        help='YAML files with data to load')
    parser.add_argument('--host',
                        help=textwrap.dedent('''Fully specified URI of the running SkyPortal instance.
                             E.g., https://myserver.com:9000.

                             Defaults to http://localhost on the port specified
                             in the SkyPortal configuration file.'''))
    parser.add_argument('--token',
                        help=textwrap.dedent('''Token required for accessing the SkyPortal API.

                             By default, SkyPortal produces a token that is
                             written to .tokens.yaml.  If no token is specified
                             here, that token will be used.'''))

    env, cfg = load_env()

    ## TODO: load multiple files
    fname = env.data_files[0]
    src = yaml.load(open(fname, "r"), Loader=Loader)

    def get_token():
        if env.token:
            return env.token

        try:
            token = yaml.load(open('.tokens.yaml'), Loader=yaml.Loader)['INITIAL_ADMIN']
            print('Token loaded from `.tokens.yaml`')
            return token
        except:
            print('Error: no token specified, and no suitable token found in .tokens.yaml')
            sys.exit(-1)

    admin_token = get_token()

    def get(endpoint, token=admin_token):
        response_status, data = api("GET", endpoint,
                                    token=token,
                                    host=env.host)
        return response_status, data

    def post(endpoint, data, token=admin_token):
        response_status, data = api("POST", endpoint,
                                    data=data,
                                    token=token,
                                    host=env.host)
        return response_status, data

    def assert_post(endpoint, data, token=admin_token):
        response_status, data = post(endpoint, data, token)
        if not response_status == 200 and data["status"] == "success":
            raise RuntimeError(
                f'API call to {endpoint} failed with status {status}: {data["message"]}'
            )
        return data

    try:
        code, data = get('sysinfo')
    except requests.exceptions.ConnectionError:
        print('Error: Could not connect to SkyPortal instance; please ensure ')
        print('       it is running at the given host/port')
        sys.exit(-1)

    if data['status'] != 'success':
        print('Error: Could not authenticate against SkyPortal; please specify a valid token.')
        sys.exit(-1)

    code, response = get('groups/public')
    if code != 200:
        print('Error: no public group found; aborting')
        sys.exit(-1)
    public_group_id = response['data']['id']

    data = src.get('data', {})
    error_log = []

    references = {
        'public_group_id': public_group_id
    }

    for endpoint in data:
        print(f'Posting to {endpoint}: ', end='')
        to_post = data[endpoint]
        if 'file' in to_post:
            post_objs = yaml.load(open(to_post['file'], 'r'), Loader=yaml.Loader)
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
                for k, v in obj.items():
                    if isinstance(v, str) and v.startswith('='):
                        obj[k] = references[v[1:]]
                    elif isinstance(v, list):
                        for n, item in enumerate(v):
                            if isinstance(item, str) and item.startswith('='):
                                v[n] = references[item[1:]]
                        obj[k] = v

                print(obj)

            except KeyError:
                print(f'\nReference {v[1:]} not found while posting to {endpoint}; skipping')
                continue

            status, response = post(endpoint, data=obj)

            print('.' if status == 200 else 'X', end='')
            if status != 200:
                error_log.append(f"/{endpoint}: {response['message']}")
                continue

            # Save all references from the response
            for field, target in saved_fields.items():
                references[target] = response['data'][field]

        print()

    if error_log:
        print("\nError log:")
        print("----------")
        print("\n".join(error_log))

        sys.exit(-1)
