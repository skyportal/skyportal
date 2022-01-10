# coding: utf-8

import sys

import os

from fink_client.consumer import AlertConsumer
from fink_client.configuration import load_credentials

from astropy.time import Time

import post_fink_alerts

token = sys.argv[1]


def fid_to_filter(fid):
    switcher = {1: 'ztfg', 2: 'ztfr', 3: 'ztfi'}
    return switcher.get(fid)


def topic_to_classification(topic):
    switcher = {
        'test_stream': 'kilonova',
        'early_sn_candidates': 'supernova',
        'sn_candidates': 'supernova',
        'early_kn_candidates': 'kilonova',
        'kn_candidates': 'kilonova',
    }
    return switcher.get(topic)


def topic_to_probability(topic):
    switcher = {
        'test_stream': 0.75,
        'early_sn_candidates': 0.5,
        'sn_candidates': 1,
        'early_kn_candidates': 0.5,
        'kn_candidates': 1,
    }
    return switcher.get(topic)


def poll_alerts() -> None:
    """Connect to and poll fink servers once.

    Parameters
    ----------
    myconfig: dic
        python dictionnary containing credentials
    topics: list of str
        List of string with topic names
    """

    conf = load_credentials()

    myconfig = {
        "username": conf['username'],
        'bootstrap.servers': conf['servers'],
        'group_id': conf['group_id'],
    }

    if conf['password'] is not None:
        myconfig['password'] = conf['password']

    maxtimeout = 5
    schema = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '../../../data/fink_data/schemas/alert.avsc'
        )
    )
    # Instantiate a consumer
    consumer = AlertConsumer(conf['mytopics'], myconfig, schema_path=schema)

    try:
        while True:

            # Poll the servers
            topic, alert, key = consumer.poll(maxtimeout)
            # Analyse output - we just print some values for example
            if topic is not None:
                if alert is not None:
                    print(alert['objectId'])
                    ztf_id = alert['objectId']
                    mjd = Time(alert['candidate']['jd'], format='jd').mjd
                    instrument = "ZTF"
                    filter = fid_to_filter(
                        alert['candidate']['fid']
                    )  # fid is filter id
                    mag = alert['candidate']['magpsf']  # to be verified
                    magerr = alert['candidate']['sigmapsf']  # to be verified
                    limiting_mag = alert['candidate']['diffmaglim']  # to be verified
                    magsys = 'ab'  # seems like it is the good magsys
                    ra = alert['candidate']['ra']
                    dec = alert['candidate']['dec']
                    print(topic_to_classification(topic))
                    post_fink_alerts.from_fink_to_skyportal(
                        topic_to_classification(topic),
                        topic_to_probability(topic),
                        ztf_id,
                        mjd,
                        instrument,
                        filter,
                        mag,
                        magerr,
                        limiting_mag,
                        magsys,
                        ra,
                        dec,
                        token,
                    )
                    topic = None
                    alert = None

            else:
                print('No alerts received in the last {} seconds'.format(maxtimeout))

    except KeyboardInterrupt:
        print('interrupted!')
        # Close the connection to the servers
        consumer.close()


poll_alerts()
