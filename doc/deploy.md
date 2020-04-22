# Deployment

SkyPortal can be deployed either with or without using Docker.
Without Docker, all services (such as the database) need to be running
locally, as described in [setup](setup).

More commonly, production deployment will use Docker images.  Here, we
discuss how to deploy via
[docker-compose](https://docs.docker.com/compose/), but much of the
same information applies when using Kubernetes, for which we have an
[example deployment](https://github.com/skyportal/deploy).

## Building the Docker images

The first step is to obtain the images to launch.  We deploy
[SkyPortal images](https://hub.docker.com/r/skyportal/web) to Docker
Hub from time to time, which you can fetch using:

```
docker pull skyportal/web
```

Otherwise, you may build the images from scratch:

```
make docker-local
```

## Starting containers

Next, we deploy two containers: `web` (the SkyPortal application) and
`db` (the PostgreSQL server).  The database is stored in a local
docker volume called `skyportal_dbdata` (see `docker volume ls`).

```
docker-compose up -d
```

Once both services are up and running, you may browse to SkyPortal at `http://localhost:9000`.

## Handling problems

You can see which containers are running with `docker-compose ps`.

Inspect the logs for the running containers using:

```
docker-compose logs web
docker-compose logs db
```

(Or, follow the logs with `docker-compose logs -f db`.)


## Adding test data

To add some test data to play with, run:

```
docker-compose run web bash -c 'source /skyportal_env/bin/activate && make load_demo_data'
```

## Stopping the deployment

You may stop both containers using:

```
docker-compose stop
```

Or stop and remove them using:

```
docker-compose down
```

This does not affect data, which lives in the `./dbdata` directory.
