# Manipulating fake streams

Requirements:

* Docker & docker compose installed on your machine
* fink-client version 2.7+ cloned somewhere

For test purposes, you can produce fake streams, and consume them. Make sure that your current user is added as a docker user, and that sure Docker is running and produce a stream of data using the `produce_fake.py` script:

```bash
python produce_fake.py
```

You might see an error message once, that you can ignore safely

```
%3|1639723497.610|FAIL|rdkafka#consumer-1| [thrd:localhost:9094/bootstrap]: 
localhost:9094/bootstrap: Connect to ipv4#127.0.0.1:9094 failed: Connection 
refused (after 1ms in state CONNECT)
```

Alerts will be produced locally on the topic `test_stream`. Then generate credententials to consume this stream:

```bash
# Fake credentials
fink_client_register -username test -password None \
  -servers 'localhost:9093, localhost:9094, localhost:9095' \
  -mytopics test_stream -group_id test_group -maxtimeout 10
```


You can then use `sample.avro/` and `schema.avsc` to produce alerts.