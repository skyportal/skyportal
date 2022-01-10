import os
import subprocess
import confluent_kafka
import pytest
import time
import yaml

from sncosmo.bandpasses import _BANDPASSES
from baselayer.app.env import load_env
from fink_client.avroUtils import AlertReader
from fink_client.avroUtils import encode_into_avro

from fink_client.consumer import AlertConsumer
from fink_client.configuration import load_credentials

from astropy.time import Time
import skyportal.utils.fink.post_fink_alerts as sa

# sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))+ '/utils/fink/')


_, cfg = load_env()
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]


_BANDPASSES


basedir = os.path.abspath(os.path.join(os.path.dirname(__file__)))

data_path = basedir + '/sample.avro'

schema_path = basedir + '/schemas/schema_test.avsc'

taxonomy_dir = basedir + '/../../../data/taxonomy_demo.yaml'


@pytest.mark.dependency()
def test_fink_registration():
    fink_registration = [
        'fink_client_register',
        '-username',
        'test',
        '-password',
        'None',
        '-servers',
        'localhost:9093',
        '-mytopics',
        'test_stream',
        '-group_id',
        'test_group',
        '-maxtimeout',
        '10',
    ]
    test = subprocess.Popen(fink_registration, cwd=basedir, preexec_fn=os.setsid)
    test.communicate()[0]
    assert test.returncode == 0


@pytest.mark.dependency(depends=['test_fink_registration'])
def test_kafka_producer():

    test = subprocess.Popen(
        ['docker-compose', 'down'], cwd=basedir, preexec_fn=os.setsid
    )
    test.communicate()[0]
    assert test.returncode == 0

    test = subprocess.Popen(
        ['docker-compose', 'up', '-d'], cwd=basedir, preexec_fn=os.setsid
    )
    test.communicate()[0]
    assert test.returncode == 0

    r = AlertReader(data_path)
    alerts = r.to_list()
    assert len(alerts) > 0
    conf = load_credentials()

    kafka_servers = conf['servers']
    #
    assert (kafka_servers is not None) and (kafka_servers is not [])

    p = confluent_kafka.Producer({'bootstrap.servers': kafka_servers})

    assert isinstance(p, confluent_kafka.Producer)
    assert p is not None

    for alert in alerts[::-1]:
        avro_data = encode_into_avro(alert, schema_path)
        topic = 'test_stream'
        try:
            p.produce(topic, avro_data)
        except ConnectionError:
            pytest.fail("Connection Error")

    p.flush()


@pytest.mark.dependency(depends=['test_kafka_producer'])
def test_fink_consumer():

    conf = load_credentials()
    myconfig = {
        "username": conf['username'],
        'bootstrap.servers': conf['servers'],
        'group_id': conf['group_id'],
    }

    if conf['password'] is not None:
        myconfig['password'] = conf['password']

    maxtimeout = 10

    # Instantiate a consumer
    consumer = AlertConsumer(conf['mytopics'], myconfig, schema_path=schema_path)

    topic, alert, key = consumer.poll(maxtimeout)

    assert topic is not None
    assert topic == 'test_stream'

    r = AlertReader(data_path)
    alerts = r.to_list()
    assert len(alerts) > 0

    assert alert is not None
    assert alerts[len(alerts) - 1]['objectId'] == alert['objectId']
    assert alerts[len(alerts) - 1]['candidate']['ra'] == alert['candidate']['ra']
    assert alerts[len(alerts) - 1]['candidate']['dec'] == alert['candidate']['dec']
    assert alerts[len(alerts) - 1]['candidate']['jd'] == alert['candidate']['jd']
    assert alerts[len(alerts) - 1]['candidate']['fid'] == alert['candidate']['fid']


@pytest.mark.dependency(depends=['test_fink_consumer'])
def test_skyportal_api(super_admin_token):
    r = AlertReader(data_path)
    alert = r.to_list()[0]
    topic = load_credentials()['mytopics'][0]

    status, id = sa.post_telescopes('ztf', 'ztf', 10, super_admin_token)
    assert status == 200
    status, id = sa.post_instruments(
        'ztf', 'imager', 1, ['ztfr', 'ztfg', 'ztfi'], super_admin_token
    )
    assert status == 200
    status, id_stream = sa.post_streams('test_stream', super_admin_token)
    assert status == 200
    status, id_filter = sa.post_filters('test_filter', id_stream, 1, super_admin_token)
    assert status == 200

    status, instruments = sa.get_all_instruments(super_admin_token)
    assert status == 200
    status, groups_dict = sa.get_group_ids_and_name(super_admin_token)
    assert status == 200
    group_ids = list(groups_dict.values())
    if topic not in list(groups_dict.keys()):
        classification = topic_to_classification(topic)
        status, id_fink = sa.post_fink_group(classification, super_admin_token)
        assert status == 200
        groups_dict[topic] = max(group_ids) + 1

    instrument = "ztf"
    if instrument in instruments.keys():
        ztf_id = alert['objectId']
        ra = alert['candidate']['ra']
        dec = alert['candidate']['dec']
        mjd = Time(alert['candidate']['jd'], format='jd').mjd
        filter = fid_to_filter(alert['candidate']['fid'])  # fid is filter id
        mag = alert['candidate']['magpsf']  # to be verified
        magerr = alert['candidate']['sigmapsf']  # to be verified
        limiting_mag = alert['candidate']['diffmaglim']
        magsys = 'ab'

        classification = topic_to_classification(topic)
        probability = topic_to_probability(topic)

        status, source_ids = sa.get_all_source_ids(token=super_admin_token)
        if ztf_id not in source_ids:
            print('this source doesnt exist yet')
            status, id = sa.post_source(
                ztf_id, ra, dec, [id_fink], token=super_admin_token
            )
            assert status == 200
        status, candidate_ids = sa.get_all_candidate_ids(token=super_admin_token)
        if ztf_id not in candidate_ids:
            print('this candidate doesnt exist yet')
            passed_at = Time(mjd, format='mjd').isot
            print(id_filter)
            status, ids = sa.post_candidate(
                ztf_id, ra, dec, [id_filter], passed_at, token=super_admin_token
            )
            assert status == 200
        instrument_id = instruments[instrument]
        time.sleep(2)
        status, id = sa.post_photometry(
            ztf_id,
            mjd,
            instrument_id,
            filter,
            mag,
            magerr,
            limiting_mag,
            magsys,
            ra,
            dec,
            [id_fink],
            [id_stream],
            token=super_admin_token,
        )
        assert status == 200

        with open(taxonomy_dir) as file:
            tax = yaml.load(file, Loader=yaml.FullLoader)
        status, taxonomy_id = sa.post_taxonomy(
            name='demo_taxonomy',
            hierarchy=tax[0]['hierarchy'],
            version='1.0.0',
            token=super_admin_token,
        )
        assert status == 200

        if sa.classification_exists_for_objs(ztf_id, token=super_admin_token):
            status = sa.update_classification(
                ztf_id,
                topic,
                probability,
                taxonomy_id,
                [groups_dict[topic]],
                token=super_admin_token,
            )
        else:
            print('this classification doesnt exist yet')
            status, classification_id = sa.post_classification(
                ztf_id,
                topic,
                probability,
                taxonomy_id,
                [groups_dict[topic]],
                token=super_admin_token,
            )
    else:
        print('error: instrument named {} does not exist'.format(instrument))


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
