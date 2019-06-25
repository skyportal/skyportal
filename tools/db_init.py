#!/usr/bin/env python

import subprocess
import sys
import argparse
import textwrap
import requests
import tempfile
import tarfile
from pathlib import Path
import os

from uuid import uuid4
from baselayer.app.env import load_env


from baselayer.tools.status import status


parser = argparse.ArgumentParser(
    description='Create or re-create the database.'
)
parser.add_argument('-f', '--force', action='store_true',
                    help='recreate the db, even if it already exists')
args, unknown = parser.parse_known_args()

env, cfg = load_env()

db = cfg['database:database']
all_dbs = (db, db + '_test')

user = cfg['database:user'] or db
host = cfg['database:host']
port = cfg['database:port']
password = cfg['database:password']
q3c_url = 'https://github.com/segasai/q3c/archive/v1.8.0.tar.gz'

psql_cmd = 'psql'
flags = f'-U {user}'

if password:
    psql_cmd = f'PGPASSWORD="{password}" {psql_cmd}'
flags += f' --no-password'

if host:
    flags += f' -h {host}'

if port:
    flags += f' -p {port}'


def run(cmd, check=False):
    return subprocess.run(cmd,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          shell=True, check=check)


def test_db(database):
    test_cmd = f"{psql_cmd} {flags} -c 'SELECT 0;' {database}"
    p = run(test_cmd)

    try:
        with status('Testing database connection'):
            if not p.returncode == 0:
                raise RuntimeError()
    except:
        print(textwrap.dedent(
            f'''
             !!! Error accessing database:

             The most common cause of database connection errors is a
             misconfigured `pg_hba.conf`.

             We tried to connect to the database with the following parameters:

               database: {db}
               username: {user}
               host:     {host}
               port:     {port}

             The postgres client exited with the following error message:

             {'-' * 78}
             {p.stderr.decode('utf-8').strip()}
             {'-' * 78}

             Please modify your `pg_hba.conf`, and use the following command to
             check your connection:

               {test_cmd}
            '''))

        sys.exit(1)

with status(f'Creating database extensions..'):

    plat = run('uname').stdout
    if b'Darwin' in plat:
        sudo = ''
    else:
        sudo = 'sudo -u postgres'


    for current_db in all_dbs:
        # create q3c extension
        result = run(f'{sudo} psql {flags} -c "CREATE EXTENSION q3c"')
        out = str(result.stdout)
        err = str(result.stderr)
        q3c_created = 'CREATE EXTENSION' in out
        if not q3c_created:
            print('could not create q3c extension. please check user permissions.')
            print(out, err)
            sys.exit(1)

with status(f'Checking database extensions..'):

    plat = run('uname').stdout
    if b'Darwin' in plat:
        sudo = ''
    else:
        sudo = 'sudo -u postgres'


    for current_db in all_dbs:
        # check if q3c is installed
        result = run(f'{sudo} psql {flags} -c "\\dx"')
        out = str(result.stdout)
        q3c_installed = 'q3c' in out

        if not q3c_installed:
            print('q3c is not installed in your postgres backend. Please install q3c.')
            sys.exit(1)
