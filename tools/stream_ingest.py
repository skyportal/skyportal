#!/usr/bin/env python

"""Note that consumers with the same group ID share a stream.
To run multiple consumers each ingesting all messages,
each consumer needs a different group.
"""

import argparse
import sys
import os
import inspect
import requests
import numpy as np

from lsst.alert.stream import alertConsumer
import baselayer
from baselayer.app.config import load_config
from skyportal.models import (init_db, Token, Source, Telescope, Instrument,
                              Photometry, DBSession, Thumbnail)
from skyportal.model_util import create_token


skyportal_root = os.path.dirname(os.path.dirname(
    os.path.abspath(inspect.getsourcefile(lambda:0))))
print('stream_ingest.py skyportal_root:', skyportal_root)
cfg = load_config([os.path.join(skyportal_root, 'test_config.yaml')])
conn = init_db(**cfg['database'])


def msg_text(message):
    """Remove postage stamp cutouts from an alert message.
    """
    message_text = {k: message[k] for k in message
                    if k not in ['cutoutDifference', 'cutoutTemplate']}
    return message_text


def write_stamp_file(stamp_dict, output_dir):
    """Given a stamp dict that follows the cutout schema,
       write data to a file in a given directory.
    """
    try:
        filename = stamp_dict['fileName']
        try:
            os.makedirs(output_dir)
        except OSError:
            pass
        out_path = os.path.join(output_dir, filename)
        with open(out_path, 'wb') as f:
            f.write(stamp_dict['stampData'])
    except TypeError:
        sys.stderr.write(f'%% Cannot get stamp\n  -- stamp_dict: {stamp_dict}')
    return


def post_to_skyportal(data, token, instrument_id):
    headers = {'Authorization': f'token {token}'}
    source = Source.query.get(str(data['diaSource']['diaSourceId']))
    if not source:
        r = requests.post('http://localhost:5000/api/sources',
                      headers=headers,
                      json={'ra': data['diaSource']['ra'],
                            'dec': data['diaSource']['decl'],
                            'id': str(data['diaSource']['diaSourceId']),
                            'group_ids': [1]})
    try:
        r = requests.post('http://localhost:5000/api/photometry',
                          headers=headers,
                          json={'source_id': str(data['diaSource']['diaSourceId']),
                                'time': data['diaObject']['radecTai'],
                                'mag': data['diaSource']['totFlux'],
                                'e_mag': data['diaSource']['totFluxErr'],
                                'time_scale': 'tai',
                                'time_format': 'mjd',
                                'instrument_id': instrument_id,
                                'lim_mag': 28,
                                'filter': ''})
    except:
        print(data)
        raise
    print(data['alertId'], r.json())


def alert_filter(alert, skyportal_token, instrument_id, stampdir=None):
    """Filter to apply to each alert.
       See schemas here: https://github.com/lsst-dm/sample-avro-alert
    """
    data = msg_text(alert)
    if data:  # Write your condition statement here
        post_to_skyportal(data, skyportal_token, instrument_id)
        if stampdir:  # Collect all postage stamps **There are no stamps**
            write_stamp_file(alert.get('cutoutDifference'), stampdir)
            write_stamp_file(alert.get('cutoutTemplate'), stampdir)
    return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('broker', type=str,
                        help='Hostname or IP and port of Kafka broker.')
    parser.add_argument('topic', type=str,
                        help='Name of Kafka topic to listen to.')
    parser.add_argument('interval', type=int,
                        help='Print every Nth alert.')
    parser.add_argument('--group', type=str,
                        help='Globally unique name of the consumer group. '
                        'Consumers in the same group will share messages '
                        '(i.e., only one consumer will receive a message, '
                        'as in a queue). Default is value of $HOSTNAME.')
    parser.add_argument('--stampDir', type=str,
                        help='Output directory for writing postage stamp'
                        'cutout files. **THERE ARE NO STAMPS RIGHT NOW.**')

    args = parser.parse_args()

    # Configure consumer connection to Kafka broker
    conf = {'bootstrap.servers': args.broker,
            'default.topic.config': {'auto.offset.reset': 'smallest'}}
    if args.group:
        conf['group.id'] = args.group
    else:
        conf['group.id'] = os.environ['HOSTNAME']


    # Retrieve or generate token for SkyPortal API auth
    token = Token.query.filter(Token.name == 'alert_stream_token').first()
    if not token:
        token = create_token(1, ['Upload data'], name='alert_stream_token')
    else:
        token = token.id


    # Retrieve or generate telescope & instrument ID
    telescope = Telescope.query.filter(Telescope.name == 'LSST').first()
    if not telescope:
        telescope = Telescope(name='LSST', nickname='LSST', lat=-30.245, lon=-70.749,
                              elevation=2663, diameter=8.4)
    instrument = Instrument.query.filter(Instrument.name == 'LSST Camera').first()
    if not instrument:
        instrument = Instrument(telescope=telescope, name='LSST Camera', type='phot',
                                band='optical')
        DBSession.add(instrument)
        DBSession.commit()
    instrument_id = instrument.id



    # Start consumer and print alert stream
    # alert_ids = []
    # source_ids = []
    # parent_source_ids = []
    # dia_object_ids = []
    with alertConsumer.AlertConsumer(args.topic, **conf) as streamReader:
        msg_count = 0
        while True:
            try:
                schema, msg = streamReader.poll()

                if msg is None:
                    continue
                else:
                    msg_count += 1
                    if msg_count % args.interval == 0:
                        # Apply filter to each alert
                        alert_filter(msg, token, instrument_id, args.stampDir)
                        # data = msg_text(msg)
                        # source_ids.append(data['diaSource']['diaSourceId'])
                        # alert_ids.append(data['alertId'])
                        # parent_source_ids.append(data['diaSource']['parentDiaSourceId'])
                        # dia_object_ids.append(data['diaSource']['diaObjectId'])
                        # print("number of unique source IDs:", len(np.unique(source_ids)))
                        # print("number of unique alert IDs:", len(np.unique(alert_ids)))
                        # print("number of unique parent source IDs:", len(np.unique([x for x in parent_source_ids if x is not None])))
                        # print("number of unique dia object IDs:", len(np.unique(dia_object_ids)))
                        # print('\n')

            except alertConsumer.EopError as e:
                # Write when reaching end of partition
                sys.stderr.write(e.message)
            except IndexError:
                sys.stderr.write('%% Data cannot be decoded\n')
            except UnicodeDecodeError:
                sys.stderr.write('%% Unexpected data format received\n')
            except KeyboardInterrupt:
                sys.stderr.write('%% Aborted by user\n')
                sys.exit()

if __name__ == "__main__":
    main()
