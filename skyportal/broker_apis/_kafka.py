"""Shared Kafka helpers for broker ingestion (confluent_kafka + Avro)."""

import io

import fastavro


def kafka_consumer_config(kafka, default_group):
    """Build a confluent_kafka Consumer config from an ``altdata['kafka']`` block
    (host/port/group_id/username/password/sasl_mechanism/auto_offset_reset)."""
    config = {
        "bootstrap.servers": f"{kafka.get('host', 'localhost')}:{kafka.get('port', 9092)}",
        "group.id": kafka.get("group_id") or default_group,
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
    """Decode the first Avro record of a Kafka message value (bytes)."""
    for record in fastavro.reader(io.BytesIO(value)):
        return record
    return None


def list_topics(kafka, default_group, timeout=10.0):
    """Topic names the cluster reports for these credentials."""
    from confluent_kafka import Consumer

    consumer = Consumer(kafka_consumer_config(kafka, default_group))
    try:
        metadata = consumer.list_topics(timeout=timeout)
        return sorted(metadata.topics)
    finally:
        consumer.close()
