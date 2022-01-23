import os
import confluent_kafka

from fink_client.avroUtils import AlertReader
from fink_client.avroUtils import encode_into_avro
from fink_client.configuration import load_credentials

data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sample.avro'))
schema_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'schemas/schema_test.avsc')
)

r = AlertReader(data_path)
alerts = r.to_list()

conf = load_credentials()

kafka_servers = conf['servers']
producer = confluent_kafka.Producer({'bootstrap.servers': kafka_servers})

for alert in alerts[::-1]:
    avro_data = encode_into_avro(alert, schema_path)
    topic = 'test_stream'
    producer.produce(topic, avro_data)
producer.flush()

print('{} alerts sent'.format(len(alerts)))
