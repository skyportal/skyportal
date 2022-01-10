# Manipulating fake streams

Requirements:

* Docker & docker compose installed on your machine
* fink-client version 2.7+ cloned somewhere

If your current user has not been added as a docker user, you need to run : 

```
sudo gpasswd -a $USER docker
newgrp docker
```

After which you should reboot your machine and/or run:

```
sudo systemctl restart docker.service
```

Testing with py.test :

First, after activating your virtual environment, run :
```
make db_clear && make db_init && make run_testing
```

Then, to run the tests :
```
py.test skyportal/tests/fink/test_fink.py
```


Testing while running an instance of skyportal (not for testing using the testing framework):

For testing purposes, you can produce fake streams, and consume them. Make sure that your current user is added as a docker user, and that sure Docker is running and produce a stream of data using the `produce_fake.py` script located in `skyportal/tests/fink/`:


```bash
sudo docker-compose up -d
python produce_fake.py
```

You might see an error message once, that you can ignore safely

```
%3|1639723497.610|FAIL|rdkafka#consumer-1| [thrd:localhost:9094/bootstrap]: 
localhost:9094/bootstrap: Connect to ipv4#127.0.0.1:9094 failed: Connection 
refused (after 1ms in state CONNECT)
```

Alerts will be produced locally on the topic `test_stream`. Then generate credententials to consume this stream by running this command in your terminal:

```bash
# Fake credentials
fink_client_register -username test -password None \
  -servers 'localhost:9093, localhost:9094, localhost:9095' \
  -mytopics test_stream -group_id test_group -maxtimeout 10
```


Then, while testing or not (using actual fink streams) to retrieve alerts and add them to skyportal you need to run `skyportal/utils/fink/post_fink_alerts.py` as such :

```
python poll_fink_alerts "your_skyportal_user_token(ex: provisionned admin)"
```