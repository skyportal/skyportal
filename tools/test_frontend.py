#!/usr/bin/env python

import os
from os.path import join as pjoin
import pathlib
import requests
import sys
import signal
import socket
import subprocess
import time

from baselayer.tools.supervisor_status import supervisor_status
from baselayer.app.model_util import clear_tables
from baselayer.tools.test_frontend import verify_server_availability

from tools import ztf_upload_avro

try:
    import pytest_randomly  # noqa
    RAND_ARGS = '--randomly-seed=1'
except ImportError:
    RAND_ARGS = ''

TEST_CONFIG = 'test_config.yaml'


if __name__ == '__main__':
    # Initialize the test database connection
    from baselayer.app.models import init_db
    from baselayer.app.config import load_config
    basedir = pathlib.Path(os.path.dirname(__file__))/'..'
    cfg = load_config([basedir/TEST_CONFIG])
    init_db(**cfg['database'])

    if len(sys.argv) > 1:
        test_spec = sys.argv[1]
    else:
        app_name = cfg['app:factory'].split('.')[0]
        test_spec = basedir/app_name/'tests'

    clear_tables()

    prep_db = subprocess.Popen(['python', 'skyportal/initial_setup.py'],
                               cwd=basedir, preexec_fn=os.setsid)
    prep_db.wait()

    l = ztf_upload_avro.LoadPTF(avro_dir=test_spec/'data/avro_files', nproc=1,
                                maxfiles=10, clobber=False, only_pure=False)
    l.runp()

    web_client = subprocess.Popen(['make', 'run_testing'],
                                  cwd=basedir, preexec_fn=os.setsid)

    print('[test_frontend] Waiting for supervisord to launch all server '
          'processes...')

    try:
        verify_server_availability(f"http://localhost:{cfg['ports:app']}")
        print('[test_frontend] Verified server availability')
        print('[test_frontend] Launching pytest on {}...'.format(test_spec))
        status = subprocess.run(f'python -m pytest -v {test_spec} {RAND_ARGS}',
                                shell=True, check=True)
    except Exception as e:
        print('[test_frontend] Could not launch server processes; '
              'terminating')
        print(e)
        raise
    finally:
        print('[test_frontend] Terminating supervisord...')
        os.killpg(os.getpgid(web_client.pid), signal.SIGTERM)
