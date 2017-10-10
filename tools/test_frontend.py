#!/usr/bin/env python

import os
from os.path import join as pjoin
import pathlib
import sys
sys.path.insert(0, pjoin(os.path.dirname(__file__), '..'))

import signal
import socket
import subprocess
import time
from baselayer.tools.supervisor_status import supervisor_status
try:
    import http.client as http
except ImportError:
    import httplib as http

from baselayer.app.model_util import clear_tables
from baselayer.app import models

TEST_CONFIG = '_test_config.yaml'


base_dir = os.path.abspath(pjoin(os.path.dirname(__file__), '..'))
if len(sys.argv) > 1:
    test_spec = sys.argv[1]
else:
    test_spec = pjoin(base_dir, 'skyportal', 'tests')


def add_test_yaml():
    print(f'Creating {TEST_CONFIG}')

    from textwrap import dedent
    with open(TEST_CONFIG, 'w') as f:
        f.write(dedent('''
            database:
                database: skyportal_test
                user: skyportal
                host: localhost
                port: 5432

            server:
                url: http://localhost:5000
                multi_user: True
                auth:
                  debug_login: True
                  google_oauth2_key:
                  google_oauth2_secret:

        '''))


def delete_test_yaml():
    os.remove(TEST_CONFIG)


if __name__ == '__main__':
    add_test_yaml()

    # Initialize the test database connection
    from baselayer.app.models import init_db
    from baselayer.app.config import load_config

    basedir = pathlib.Path(os.path.dirname(__file__))/'..'
    cfg = load_config([basedir/TEST_CONFIG])
    init_db(**cfg['database'])

    clear_tables()

    web_client = subprocess.Popen(['make', 'testrun'], cwd=base_dir,
                                  preexec_fn=os.setsid)

    print('[test_frontend] Waiting for supervisord to launch all server processes...')

    try:
        timeout = 0
        while ((timeout < 30) and
               (not all([b'RUNNING' in line for line in supervisor_status()]))):
            time.sleep(1)
            timeout += 1

        if timeout == 10:
            print('[test_frontend] Could not launch server processes; terminating')
            sys.exit(-1)

        for timeout in range(10):
            conn = http.HTTPConnection("localhost", 5000)
            try:
                conn.request('HEAD', '/')
                status = conn.getresponse().status
                if status == 200:
                    break
            except socket.error:
                pass
            time.sleep(1)
        else:
            raise socket.error("Could not connect to localhost:5000.")

        if status != 200:
            print('[test_frontend] Server status is {} instead of 200'.format(
                status))
            sys.exit(-1)
        else:
            print('[test_frontend] Verified server availability')

        print('[test_frontend] Launching pytest on {}...'.format(test_spec))

        status = subprocess.run(f'python -m pytest -v {test_spec}', shell=True,
                                check=True)
    except:
        raise
    finally:
        print('[test_frontend] Terminating supervisord...')
        os.killpg(os.getpgid(web_client.pid), signal.SIGTERM)
        delete_test_yaml()
