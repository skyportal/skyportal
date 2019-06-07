#!/usr/bin/env python

"""Consumes stream for printing all messages to the console.

Note that consumers with the same group ID share a stream.
To run multiple consumers each printing all messages,
each consumer needs a different group.
"""

import argparse
import sys
import os
import requests

from lsst.alert.stream import alertConsumer
import baselayer
from baselayer.app.config import load_config
from skyportal.models import init_db, Token
from skyportal.model_util import create_token


conn = init_db(**load_config()['database'])


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
        sys.stderr.write('%% Cannot get stamp\n')
    return


def post_to_skyportal(data):
    token = Token.query.filter(Token.name=='alert_stream_token').first()
    if not token:
        token = create_token(1, ['Upload data'], name='alert_stream_token')
    else:
        token = token.id
    headers = {'Authorization': f'token {token}'}
    r = requests.post('http://localhost:5000/api/sources',
                      headers=headers,
                      json={'ra': data['diaSource']['ra'],
                            'dec': data['diaSource']['decl'],
                            'id': str(data['alertId']),
                            'group_ids': [1]})
    print(data['alertId'], r.json())


def alert_filter(alert, stampdir=None):
    """Filter to apply to each alert.
       See schemas here: https://github.com/lsst-dm/sample-avro-alert
    """
    data = msg_text(alert)
    if data:  # Write your condition statement here
        post_to_skyportal(data)
        if stampdir:  # Collect all postage stamps **There are no stamps**
            write_stamp_file(
                alert.get('cutoutDifference'), stampdir)
            write_stamp_file(
                alert.get('cutoutTemplate'), stampdir)
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

    # Start consumer and print alert stream
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
                        alert_filter(msg, args.stampDir)

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
