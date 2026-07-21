"""Shared Kafka helpers for broker ingestion (confluent_kafka + Avro).

Every Kafka-based provider (babamul, BOOM, ...) builds the same consumer config
from a broker's ``altdata['kafka']`` block and decodes Avro the same way; keep it
here rather than re-deriving it per provider.
"""


def kafka_consumer_config(kafka, default_group):
    """Build a confluent_kafka Consumer config from an ``altdata['kafka']`` block
    (host/port/group_id/username/password/sasl_mechanism/auto_offset_reset)."""
    config = {
        "bootstrap.servers": f"{kafka.get('host', 'localhost')}:{kafka.get('port', 9092)}",
        "group.id": kafka.get("group_id", default_group),
        "auto.offset.reset": kafka.get("auto_offset_reset", "earliest"),
        "security.protocol": "PLAINTEXT",
    }
    if kafka.get("username"):
        config.update(
            {
                "security.protocol": "SASL_PLAINTEXT",
                "sasl.mechanism": kafka.get("sasl_mechanism", "SCRAM-SHA-512"),
                "sasl.username": kafka["username"],
                "sasl.password": kafka["password"],
            }
        )
    return config


def read_avro(value):
    """Decode a single Avro record from a Kafka message value (bytes)."""
    import io

    import fastavro

    for record in fastavro.reader(io.BytesIO(value)):
        return record
    return None
