#!/usr/bin/env python
# Copyright 2021 AstroLab Software
# Author: Julien Peloton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import confluent_kafka

import numpy as np

from fink_client.avroUtils import AlertReader
from fink_client.avroUtils import encode_into_avro

from fink_client.configuration import load_credentials

data_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'sample.avro'))
schema_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    '../schemas/schema_test.avsc'))

r = AlertReader(data_path)
alerts = r.to_list()

conf = load_credentials(tmp=True)

kafka_servers = conf['servers']
p = confluent_kafka.Producer({
    'bootstrap.servers': kafka_servers})

for alert in alerts[::-1]:
    avro_data = encode_into_avro(alert, schema_path)
    topic = 'test_stream'
    p.produce(topic, avro_data)
p.flush()

print('{} alerts sent'.format(len(alerts)))
